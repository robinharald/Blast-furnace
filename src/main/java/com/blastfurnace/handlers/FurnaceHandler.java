package com.blastfurnace.handlers;

import com.blastfurnace.core.BarType;
import com.blastfurnace.core.BotConfig;
import com.blastfurnace.utils.SleepUtils;
import org.dreambot.api.methods.container.impl.Inventory;
import org.dreambot.api.methods.container.impl.equipment.Equipment;
import org.dreambot.api.methods.interactive.GameObjects;
import org.dreambot.api.methods.interactive.Players;
import org.dreambot.api.methods.map.Area;
import org.dreambot.api.methods.map.Tile;
import org.dreambot.api.methods.walking.impl.Walking;
import org.dreambot.api.methods.widget.Widgets;
import org.dreambot.api.utilities.Sleep;
import org.dreambot.api.wrappers.interactive.GameObject;
import org.dreambot.api.wrappers.items.Item;

/**
 * Handles all furnace interactions:
 * - Walking to and using the conveyor belt
 * - Depositing ores and coal
 * - Walking to the bar dispenser
 * - Collecting smelted bars
 * - Equipping/swapping gloves as needed
 */
public class FurnaceHandler {

    private static final Area BANK_AREA = new Area(
            BotConfig.BANK_AREA_X_MIN, BotConfig.BANK_AREA_Y_MIN,
            BotConfig.BANK_AREA_X_MAX, BotConfig.BANK_AREA_Y_MAX);
    private static final Tile CONVEYOR_TILE = new Tile(
            BotConfig.CONVEYOR_TILE_X, BotConfig.CONVEYOR_TILE_Y, 0);
    private static final Tile DISPENSER_TILE = new Tile(
            BotConfig.DISPENSER_TILE_X, BotConfig.DISPENSER_TILE_Y, 0);

    private final BotConfig config;
    private final CoalBagHandler coalBagHandler;

    public FurnaceHandler(BotConfig config, CoalBagHandler coalBagHandler) {
        this.config = config;
        this.coalBagHandler = coalBagHandler;
    }

    /**
     * Walk to the conveyor belt area.
     */
    public boolean walkToConveyor() {
        if (isNearConveyor()) return true;
        Walking.walk(CONVEYOR_TILE);
        Sleep.sleepUntil(this::isNearConveyor, BotConfig.WALK_TIMEOUT);
        SleepUtils.actionDelay();
        return isNearConveyor();
    }

    /**
     * Walk to the bar dispenser.
     */
    public boolean walkToDispenser() {
        if (isNearDispenser()) return true;
        Walking.walk(DISPENSER_TILE);
        Sleep.sleepUntil(this::isNearDispenser, BotConfig.WALK_TIMEOUT);
        SleepUtils.actionDelay();
        return isNearDispenser();
    }

    /**
     * Walk back to the bank area.
     */
    public boolean walkToBank() {
        if (isInBankArea()) return true;
        Walking.walk(BANK_AREA.getRandomTile());
        Sleep.sleepUntil(this::isInBankArea, BotConfig.WALK_TIMEOUT);
        SleepUtils.actionDelay();
        return isInBankArea();
    }

    /**
     * Deposit items on the conveyor belt.
     * For coal bars: deposits coal bag contents first, then inventory items.
     */
    public boolean depositOnConveyor(BarType barType) {
        GameObject conveyor = GameObjects.closest(BotConfig.CONVEYOR_BELT_ID);
        if (conveyor == null) return false;

        // For bars that need coal and we have coal in the bag, empty bag first
        if (barType.requiresCoal() && config.isUseCoalBag() && !coalBagHandler.isEmpty()) {
            // Put items on conveyor first
            if (conveyor.interact("Put-ore-on")) {
                Sleep.sleepUntil(() -> isConveyorIdle(), BotConfig.INTERACTION_TIMEOUT);
                SleepUtils.actionDelay();
            }

            // Empty coal bag
            coalBagHandler.emptyOnConveyor();
            SleepUtils.actionDelay();

            // If there's remaining coal from the bag in inventory, put it on too
            if (Inventory.contains(BotConfig.COAL_ID)) {
                if (conveyor.interact("Put-ore-on")) {
                    Sleep.sleepUntil(() -> isConveyorIdle(), BotConfig.INTERACTION_TIMEOUT);
                    SleepUtils.actionDelay();
                }
            }
        } else {
            // Simple deposit: put everything on conveyor
            if (conveyor.interact("Put-ore-on")) {
                Sleep.sleepUntil(() -> isConveyorIdle(), BotConfig.INTERACTION_TIMEOUT);
                SleepUtils.actionDelay();
            }
        }

        // Verify inventory is (mostly) empty of ores
        return !Inventory.contains(barType.getPrimaryOreId());
    }

    /**
     * Collect bars from the bar dispenser.
     * Handles glove swapping for gold bars (goldsmith -> ice gloves).
     */
    public boolean collectBars(BarType barType) {
        // For gold bars: swap to ice gloves before collecting if needed
        if (barType == BarType.GOLD && config.isUseIceGloves()) {
            equipIceGloves();
        }

        GameObject dispenser = GameObjects.closest(BotConfig.BAR_DISPENSER_ID);
        if (dispenser == null) return false;

        if (dispenser.interact("Take")) {
            Sleep.sleepUntil(this::isBarWidgetOpen, BotConfig.INTERACTION_TIMEOUT);
            SleepUtils.actionDelay();
        }

        // Click on the bar in the collection widget
        if (isBarWidgetOpen()) {
            // Click the bar to collect all
            var barWidget = Widgets.getWidget(BotConfig.BAR_DISPENSER_WIDGET_PARENT);
            if (barWidget != null) {
                var child = barWidget.getChild(BotConfig.BAR_DISPENSER_WIDGET_CHILD);
                if (child != null) {
                    child.interact();
                    Sleep.sleepUntil(() -> Inventory.contains(barType.getBarId()), 3000);
                    SleepUtils.actionDelay();
                }
            }
        }

        return Inventory.contains(barType.getBarId());
    }

    /**
     * Equip ice gloves for bar collection.
     */
    public boolean equipIceGloves() {
        if (Equipment.contains(BotConfig.ICE_GLOVES_ID)) return true;

        Item gloves = Inventory.get(BotConfig.ICE_GLOVES_ID);
        if (gloves != null) {
            gloves.interact("Wear");
            Sleep.sleepUntil(() -> Equipment.contains(BotConfig.ICE_GLOVES_ID), 2000);
            SleepUtils.actionDelay();
            return Equipment.contains(BotConfig.ICE_GLOVES_ID);
        }
        return false;
    }

    /**
     * Equip goldsmith gauntlets for gold ore smelting XP.
     */
    public boolean equipGoldsmithGauntlets() {
        if (Equipment.contains(BotConfig.GOLDSMITH_GAUNTLETS_ID)) return true;

        Item gloves = Inventory.get(BotConfig.GOLDSMITH_GAUNTLETS_ID);
        if (gloves != null) {
            gloves.interact("Wear");
            Sleep.sleepUntil(() -> Equipment.contains(BotConfig.GOLDSMITH_GAUNTLETS_ID), 2000);
            SleepUtils.actionDelay();
            return Equipment.contains(BotConfig.GOLDSMITH_GAUNTLETS_ID);
        }
        return false;
    }

    /**
     * Check if we're near the conveyor belt.
     */
    public boolean isNearConveyor() {
        return Players.getLocal().distance(CONVEYOR_TILE) <= 3;
    }

    /**
     * Check if we're near the bar dispenser.
     */
    public boolean isNearDispenser() {
        return Players.getLocal().distance(DISPENSER_TILE) <= 3;
    }

    /**
     * Check if we're in the bank area.
     */
    public boolean isInBankArea() {
        return BANK_AREA.contains(Players.getLocal());
    }

    /**
     * Check if the bar collection widget is open.
     */
    private boolean isBarWidgetOpen() {
        var widget = Widgets.getWidget(BotConfig.BAR_DISPENSER_WIDGET_PARENT);
        return widget != null && widget.isVisible();
    }

    /**
     * Check if the conveyor interaction has completed.
     */
    private boolean isConveyorIdle() {
        return !Players.getLocal().isAnimating() && !Players.getLocal().isMoving();
    }
}
