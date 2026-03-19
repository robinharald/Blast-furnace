package com.blastfurnace.handlers;

import com.blastfurnace.core.BotConfig;
import org.dreambot.api.methods.container.impl.Inventory;
import org.dreambot.api.methods.container.impl.bank.Bank;
import org.dreambot.api.methods.interactive.Players;
import org.dreambot.api.utilities.Sleep;
import org.dreambot.api.wrappers.items.Item;

/**
 * Manages the coal bag: filling, emptying, and keeping it in a locked inventory slot.
 *
 * The coal bag holds 27 coal (or 36 with the upgraded version).
 * It occupies a fixed slot in the inventory and should never be deposited.
 */
public class CoalBagHandler {

    private static final int COAL_BAG_CAPACITY = 27;
    private final BotConfig config;
    private int coalInBag = 0;

    public CoalBagHandler(BotConfig config) {
        this.config = config;
    }

    /**
     * Check if the coal bag is present in the inventory.
     */
    public boolean hasBag() {
        return Inventory.contains(BotConfig.COAL_BAG_ID) || Inventory.contains(BotConfig.COAL_BAG_OPEN_ID);
    }

    /**
     * Fill the coal bag from the bank.
     * Must be called while the bank is open.
     * Uses the bank interface to fill the coal bag without closing the bank.
     */
    public boolean fillFromBank() {
        Item bag = Inventory.get(item ->
                item != null && (item.getID() == BotConfig.COAL_BAG_ID || item.getID() == BotConfig.COAL_BAG_OPEN_ID));
        if (bag == null) return false;

        // If there's residual coal in the bag, empty it first into the bank
        if (coalInBag > 0) {
            bag.interact("Empty");
            Sleep.sleepUntil(() -> false, 600);
        }

        // Fill the coal bag
        bag.interact("Fill");
        Sleep.sleepUntil(() -> false, 600);
        coalInBag = Math.min(COAL_BAG_CAPACITY, getCoalCountInBank());
        return true;
    }

    /**
     * Empty the coal bag onto the conveyor belt.
     * Should be called while standing at the conveyor.
     */
    public boolean emptyOnConveyor() {
        Item bag = Inventory.get(item ->
                item != null && (item.getID() == BotConfig.COAL_BAG_ID || item.getID() == BotConfig.COAL_BAG_OPEN_ID));
        if (bag == null || coalInBag <= 0) return false;

        bag.interact("Empty");
        Sleep.sleepUntil(() -> !Players.getLocal().isAnimating(), 2000);
        coalInBag = 0;
        return true;
    }

    /**
     * Get the coal bag item from inventory.
     */
    public Item getBagItem() {
        return Inventory.get(item ->
                item != null && (item.getID() == BotConfig.COAL_BAG_ID || item.getID() == BotConfig.COAL_BAG_OPEN_ID));
    }

    /**
     * Track coal count in the bag.
     */
    public int getCoalInBag() {
        return coalInBag;
    }

    public void setCoalInBag(int count) {
        this.coalInBag = Math.min(count, COAL_BAG_CAPACITY);
    }

    public boolean isFull() {
        return coalInBag >= COAL_BAG_CAPACITY;
    }

    public boolean isEmpty() {
        return coalInBag <= 0;
    }

    /**
     * Ensure the coal bag is in the locked slot during banking.
     * If it's been accidentally deposited, withdraw it.
     */
    public boolean ensureBagInInventory() {
        if (hasBag()) return true;

        if (Bank.isOpen()) {
            if (Bank.contains(BotConfig.COAL_BAG_ID) || Bank.contains(BotConfig.COAL_BAG_OPEN_ID)) {
                Bank.withdraw(BotConfig.COAL_BAG_ID, 1);
                Sleep.sleepUntil(this::hasBag, 2000);
                return hasBag();
            }
        }
        return false;
    }

    /**
     * When banking, deposit all items EXCEPT the coal bag.
     * This prevents accidentally banking the coal bag.
     */
    public boolean isCoalBag(int itemId) {
        return itemId == BotConfig.COAL_BAG_ID || itemId == BotConfig.COAL_BAG_OPEN_ID;
    }

    private int getCoalCountInBank() {
        if (!Bank.isOpen()) return 0;
        Item coal = Bank.get(BotConfig.COAL_ID);
        return coal != null ? coal.getAmount() : 0;
    }
}
