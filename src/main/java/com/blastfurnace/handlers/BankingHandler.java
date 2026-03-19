package com.blastfurnace.handlers;

import com.blastfurnace.core.BarType;
import com.blastfurnace.core.BotConfig;
import com.blastfurnace.utils.SleepUtils;
import org.dreambot.api.methods.container.impl.Inventory;
import org.dreambot.api.methods.container.impl.bank.Bank;
import org.dreambot.api.methods.container.impl.equipment.Equipment;
import org.dreambot.api.methods.interactive.GameObjects;
import org.dreambot.api.methods.map.Tile;
import org.dreambot.api.methods.walking.impl.Walking;
import org.dreambot.api.utilities.Sleep;
import org.dreambot.api.wrappers.items.Item;

/**
 * Handles all banking operations for the Blast Furnace:
 * - Opening the bank chest
 * - Depositing bars (excluding coal bag)
 * - Withdrawing ores, stamina potions, and gloves
 * - Filling the coal bag
 * - Checking supplies
 */
public class BankingHandler {

    private final BotConfig config;
    private final CoalBagHandler coalBagHandler;

    // Tracks which trip we're on for coal-loading cycles
    private int coalTripCounter = 0;
    private boolean needsOreTrip = false;

    public BankingHandler(BotConfig config, CoalBagHandler coalBagHandler) {
        this.config = config;
        this.coalBagHandler = coalBagHandler;
    }

    /**
     * Open the bank chest if not already open.
     */
    public boolean openBank() {
        if (Bank.isOpen()) return true;

        var bankChest = GameObjects.closest(BotConfig.BANK_CHEST_ID);
        if (bankChest != null && bankChest.interact("Use")) {
            Sleep.sleepUntil(Bank::isOpen, BotConfig.INTERACTION_TIMEOUT);
            SleepUtils.actionDelay();
        }
        return Bank.isOpen();
    }

    /**
     * Deposit all items except the coal bag into the bank.
     */
    public boolean depositInventory() {
        if (!Bank.isOpen()) return false;

        // Deposit all except coal bag
        for (Item item : Inventory.all()) {
            if (item != null && !coalBagHandler.isCoalBag(item.getID())) {
                Bank.deposit(item.getID(), Bank.Amount.ALL);
                SleepUtils.actionDelay();
            }
        }

        Sleep.sleepUntil(() -> {
            int count = 0;
            for (Item item : Inventory.all()) {
                if (item != null && !coalBagHandler.isCoalBag(item.getID())) count++;
            }
            return count == 0;
        }, 3000);

        return true;
    }

    /**
     * Full banking sequence: deposit bars, withdraw ores, fill coal bag.
     * Returns true if inventory is properly set up for the next trip.
     */
    public boolean performBanking(BarType barType) {
        if (!openBank()) return false;

        // Deposit everything except coal bag
        depositInventory();
        SleepUtils.actionDelay();

        // Ensure coal bag is in inventory
        if (config.isUseCoalBag() && barType.requiresCoal()) {
            coalBagHandler.ensureBagInInventory();
            SleepUtils.actionDelay();
        }

        // Check stamina
        if (config.isUseStaminaPotions()) {
            handleStamina();
        }

        // Determine what to withdraw based on bar type and trip cycle
        if (barType.requiresCoal()) {
            return handleCoalBarWithdrawal(barType);
        } else if (barType.hasTwoOres()) {
            return handleTwoOreWithdrawal(barType);
        } else {
            return handleSimpleOreWithdrawal(barType);
        }
    }

    /**
     * Handle withdrawals for bars that require coal (steel, mithril, adamant, rune).
     * Uses a trip counter to alternate between coal-only and ore trips.
     */
    private boolean handleCoalBarWithdrawal(BarType barType) {
        int coalPerBar = barType.getCoalPerBar();

        if (config.isUseCoalBag()) {
            // With coal bag: fill the bag with coal every trip
            coalBagHandler.fillFromBank();
            SleepUtils.actionDelay();

            if (coalTripCounter < coalPerBar - 1) {
                // Coal-loading trip: fill inventory with coal too
                withdrawItem(BotConfig.COAL_ID, 27);
                coalTripCounter++;
                needsOreTrip = false;
            } else {
                // Ore trip: withdraw primary ore
                withdrawItem(barType.getPrimaryOreId(), 27);
                coalTripCounter = 0;
                needsOreTrip = true;
            }
        } else {
            // Without coal bag: alternate coal and ore trips
            if (!needsOreTrip) {
                withdrawItem(BotConfig.COAL_ID, 28);
                coalTripCounter++;
                if (coalTripCounter >= coalPerBar) {
                    needsOreTrip = true;
                    coalTripCounter = 0;
                }
            } else {
                withdrawItem(barType.getPrimaryOreId(), 28);
                needsOreTrip = false;
            }
        }

        return hasRequiredItems(barType);
    }

    /**
     * Handle bronze bars (two different ores, no coal).
     */
    private boolean handleTwoOreWithdrawal(BarType barType) {
        int halfInv = 14;
        withdrawItem(barType.getPrimaryOreId(), halfInv);
        SleepUtils.actionDelay();
        withdrawItem(barType.getSecondaryOreId(), halfInv);
        return hasRequiredItems(barType);
    }

    /**
     * Handle simple ore bars (iron, silver, gold) - just fill inventory with ore.
     */
    private boolean handleSimpleOreWithdrawal(BarType barType) {
        // For gold with goldsmith gauntlets, ensure gauntlets are equipped
        if (barType == BarType.GOLD && config.isUseGoldsmithGauntlets()) {
            if (!Equipment.contains(BotConfig.GOLDSMITH_GAUNTLETS_ID)) {
                withdrawAndEquip(BotConfig.GOLDSMITH_GAUNTLETS_ID);
                SleepUtils.actionDelay();
            }
        }

        int amount = coalBagHandler.hasBag() ? 27 : 28;
        withdrawItem(barType.getPrimaryOreId(), amount);
        return hasRequiredItems(barType);
    }

    /**
     * Handle stamina potion drinking when run energy is low.
     */
    private void handleStamina() {
        if (Walking.getRunEnergy() > BotConfig.STAMINA_THRESHOLD) return;

        // Check if already have stamina effect
        // Try to drink from inventory first, then withdraw
        Item stam = Inventory.get(item -> item != null && isStaminaPotion(item.getID()));
        if (stam == null) {
            // Withdraw a 1-dose stamina
            if (Bank.contains(BotConfig.STAMINA_POTION_1_ID)) {
                Bank.withdraw(BotConfig.STAMINA_POTION_1_ID, 1);
                Sleep.sleepUntil(() -> Inventory.contains(BotConfig.STAMINA_POTION_1_ID), 2000);
                SleepUtils.actionDelay();
            } else if (Bank.contains(BotConfig.STAMINA_POTION_2_ID)) {
                Bank.withdraw(BotConfig.STAMINA_POTION_2_ID, 1);
                Sleep.sleepUntil(() -> Inventory.contains(BotConfig.STAMINA_POTION_2_ID), 2000);
                SleepUtils.actionDelay();
            }
        }

        // Close bank, drink, re-open
        stam = Inventory.get(item -> item != null && isStaminaPotion(item.getID()));
        if (stam != null) {
            Bank.close();
            Sleep.sleepUntil(() -> !Bank.isOpen(), 2000);
            stam.interact("Drink");
            SleepUtils.actionDelay();
            // Deposit empty vial
            openBank();
            SleepUtils.actionDelay();
            if (Inventory.contains(229)) { // empty vial
                Bank.deposit(229, Bank.Amount.ALL);
                SleepUtils.actionDelay();
            }
        }
    }

    /**
     * Withdraw a specific item from the bank.
     */
    private boolean withdrawItem(int itemId, int amount) {
        if (!Bank.isOpen()) return false;
        if (!Bank.contains(itemId)) return false;

        Bank.withdraw(itemId, amount);
        Sleep.sleepUntil(() -> Inventory.contains(itemId), 2000);
        SleepUtils.actionDelay();
        return Inventory.contains(itemId);
    }

    /**
     * Withdraw and equip an item (used for gloves).
     */
    private boolean withdrawAndEquip(int itemId) {
        if (!Bank.isOpen()) return false;
        if (Equipment.contains(itemId)) return true;

        Bank.withdraw(itemId, 1);
        Sleep.sleepUntil(() -> Inventory.contains(itemId), 2000);
        SleepUtils.actionDelay();

        Bank.close();
        Sleep.sleepUntil(() -> !Bank.isOpen(), 2000);

        Item gloves = Inventory.get(itemId);
        if (gloves != null) {
            gloves.interact("Wear");
            Sleep.sleepUntil(() -> Equipment.contains(itemId), 2000);
            SleepUtils.actionDelay();
        }

        return Equipment.contains(itemId);
    }

    /**
     * Check if we have the necessary items for the current trip.
     */
    private boolean hasRequiredItems(BarType barType) {
        if (barType.requiresCoal()) {
            return Inventory.contains(BotConfig.COAL_ID) || Inventory.contains(barType.getPrimaryOreId());
        }
        if (barType.hasTwoOres()) {
            return Inventory.contains(barType.getPrimaryOreId()) && Inventory.contains(barType.getSecondaryOreId());
        }
        return Inventory.contains(barType.getPrimaryOreId());
    }

    /**
     * Check if the coffer has enough funds and refill if needed.
     */
    public boolean checkAndRefillCoffer() {
        var coffer = GameObjects.closest(BotConfig.COFFER_ID);
        if (coffer == null) return false;

        // Check coffer via varbit if possible, or interact
        coffer.interact("Use");
        SleepUtils.transitionDelay();
        return true;
    }

    /**
     * Check if we have enough supplies in the bank to continue.
     */
    public boolean hasSupplies(BarType barType) {
        if (!Bank.isOpen()) return false;

        boolean hasOre = Bank.contains(barType.getPrimaryOreId());
        if (barType.requiresCoal()) {
            hasOre = hasOre && Bank.contains(BotConfig.COAL_ID);
        }
        if (barType.hasTwoOres()) {
            hasOre = hasOre && Bank.contains(barType.getSecondaryOreId());
        }
        return hasOre;
    }

    public int getCoalTripCounter() { return coalTripCounter; }
    public boolean isNeedsOreTrip() { return needsOreTrip; }

    public void resetTripCounter() {
        coalTripCounter = 0;
        needsOreTrip = false;
    }

    private boolean isStaminaPotion(int id) {
        return id == BotConfig.STAMINA_POTION_1_ID
                || id == BotConfig.STAMINA_POTION_2_ID
                || id == BotConfig.STAMINA_POTION_3_ID
                || id == BotConfig.STAMINA_POTION_4_ID;
    }
}
