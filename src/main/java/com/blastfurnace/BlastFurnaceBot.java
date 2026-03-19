package com.blastfurnace;

import com.blastfurnace.core.BarType;
import com.blastfurnace.core.BotConfig;
import com.blastfurnace.core.BotState;
import com.blastfurnace.handlers.BankingHandler;
import com.blastfurnace.handlers.CoalBagHandler;
import com.blastfurnace.handlers.FurnaceHandler;
import com.blastfurnace.ui.ConfigGUI;
import com.blastfurnace.ui.PaintOverlay;
import com.blastfurnace.ui.StatsTracker;
import com.blastfurnace.utils.AntiPattern;
import com.blastfurnace.utils.SleepUtils;
import org.dreambot.api.methods.container.impl.Inventory;
import org.dreambot.api.methods.container.impl.bank.Bank;
import org.dreambot.api.methods.container.impl.equipment.Equipment;
import org.dreambot.api.methods.interactive.Players;
import org.dreambot.api.methods.map.Tile;
import org.dreambot.api.methods.walking.impl.Walking;
import org.dreambot.api.script.AbstractScript;
import org.dreambot.api.script.Category;
import org.dreambot.api.script.ScriptManifest;
import org.dreambot.api.utilities.Sleep;

import java.awt.*;

/**
 * OSRS Blast Furnace Bot
 *
 * A robust, plug-and-play bot for the Blast Furnace minigame.
 * Supports all bar types: Bronze, Iron, Silver, Steel, Gold, Mithril, Adamantite, Runite.
 *
 * Features:
 * - State machine architecture for reliable operation
 * - Coal bag with locked inventory slot
 * - Automatic stamina potion management
 * - Goldsmith gauntlets / Ice gloves swapping
 * - Intelligent coal-loading trip cycles
 * - Anti-pattern human-like behavior
 * - Live statistics paint overlay
 * - Configuration GUI
 *
 * Prerequisites:
 * - Must be standing at the Blast Furnace in Keldagrim
 * - Coffer must have gold deposited before starting
 * - Required items in bank: ores, coal (if applicable), stamina potions
 * - Coal bag in inventory (will be locked in place)
 * - Ice gloves equipped or in bank
 * - Goldsmith gauntlets equipped or in bank (for gold bars)
 */
@ScriptManifest(
        name = "Blast Furnace Bot",
        description = "Smelts all bar types at the Blast Furnace. Supports coal bag, stamina potions, glove swapping.",
        author = "BlastFurnaceBot",
        version = 1.0,
        category = Category.SMITHING
)
public class BlastFurnaceBot extends AbstractScript {

    private BotConfig config;
    private BotState state;
    private CoalBagHandler coalBagHandler;
    private BankingHandler bankingHandler;
    private FurnaceHandler furnaceHandler;
    private StatsTracker stats;
    private PaintOverlay paint;

    // Trip tracking
    private int coalTripsRemaining = 0;
    private boolean waitingForBars = false;
    private int inventoryOreCount = 0;

    @Override
    public void onStart() {
        config = new BotConfig();

        // Show configuration GUI
        ConfigGUI gui = new ConfigGUI(config);
        if (!gui.show()) {
            log("Bot cancelled by user.");
            stop();
            return;
        }

        // Initialize handlers
        coalBagHandler = new CoalBagHandler(config);
        bankingHandler = new BankingHandler(config, coalBagHandler);
        furnaceHandler = new FurnaceHandler(config, coalBagHandler);
        stats = new StatsTracker(config.getSelectedBar(), config.isUseGoldsmithGauntlets());
        paint = new PaintOverlay(stats);

        // Initialize coal trip counter for bars that need coal
        BarType bar = config.getSelectedBar();
        if (bar.requiresCoal() && config.isUseCoalBag()) {
            coalTripsRemaining = bar.getCoalPerBar() - 1;
        }

        state = BotState.BANKING;
        log("Blast Furnace Bot started - Smelting: " + bar.getBarName());
        log("Coal per bar: " + bar.getCoalPerBar() + " | Requires coal: " + bar.requiresCoal());
    }

    @Override
    public int onLoop() {
        if (state == BotState.STOPPED) return -1;

        // Anti-pattern behavior
        AntiPattern.performIfDue();

        // Ensure run is enabled
        if (!Walking.isRunEnabled() && Walking.getRunEnergy() > 15) {
            Walking.toggleRun();
            SleepUtils.actionDelay();
        }

        switch (state) {
            case BANKING:
                return handleBanking();
            case WALK_TO_CONVEYOR:
                return handleWalkToConveyor();
            case DEPOSIT_ORE:
                return handleDepositOre();
            case WALK_TO_DISPENSER:
                return handleWalkToDispenser();
            case COLLECT_BARS:
                return handleCollectBars();
            case WALK_TO_BANK:
                return handleWalkToBank();
            case WAITING:
                return handleWaiting();
            default:
                state = BotState.BANKING;
                return 600;
        }
    }

    /**
     * BANKING state: deposit bars, withdraw supplies, fill coal bag.
     */
    private int handleBanking() {
        // Walk to bank if not there
        if (!furnaceHandler.isInBankArea()) {
            furnaceHandler.walkToBank();
            return loopDelay();
        }

        BarType bar = config.getSelectedBar();

        // Open bank and perform banking
        if (!bankingHandler.openBank()) return loopDelay();

        // Check if we have supplies
        if (!bankingHandler.hasSupplies(bar)) {
            log("Out of supplies! Stopping bot.");
            state = BotState.STOPPED;
            return -1;
        }

        // Perform the full banking sequence
        if (bankingHandler.performBanking(bar)) {
            Bank.close();
            Sleep.sleepUntil(() -> !Bank.isOpen(), 2000);

            // Track ore count for stats
            inventoryOreCount = Inventory.count(bar.getPrimaryOreId());
            if (bar.hasTwoOres()) {
                inventoryOreCount += Inventory.count(bar.getSecondaryOreId());
            }

            stats.addTrip();

            // For gold: ensure goldsmith gauntlets are equipped before conveyor
            if (bar == BarType.GOLD && config.isUseGoldsmithGauntlets()) {
                furnaceHandler.equipGoldsmithGauntlets();
            }

            state = BotState.WALK_TO_CONVEYOR;
            log("Banking complete, heading to conveyor.");
        }

        return loopDelay();
    }

    /**
     * WALK_TO_CONVEYOR state: walk from bank to the conveyor belt.
     */
    private int handleWalkToConveyor() {
        if (furnaceHandler.walkToConveyor()) {
            state = BotState.DEPOSIT_ORE;
        }
        return loopDelay();
    }

    /**
     * DEPOSIT_ORE state: deposit ores and coal onto the conveyor belt.
     */
    private int handleDepositOre() {
        BarType bar = config.getSelectedBar();

        if (furnaceHandler.depositOnConveyor(bar)) {
            // Track ore/coal usage
            int oreDeposited = inventoryOreCount;
            stats.addOreUsed(oreDeposited);
            if (Inventory.contains(BotConfig.COAL_ID)) {
                stats.addCoalUsed(Inventory.count(BotConfig.COAL_ID));
            }

            // Determine next state based on whether we're doing a coal-only trip
            // or if bars should be ready to collect
            if (shouldCollectBars(bar)) {
                state = BotState.WALK_TO_DISPENSER;
            } else {
                // More coal trips needed, go back to bank
                state = BotState.WALK_TO_BANK;
            }
        }
        return loopDelay();
    }

    /**
     * Determine if bars should be ready for collection after this deposit.
     * For coal-requiring bars, we only collect after depositing the primary ore.
     */
    private boolean shouldCollectBars(BarType bar) {
        if (!bar.requiresCoal()) return true;

        // If this trip had ore (not just coal), bars should be smelting
        return bankingHandler.isNeedsOreTrip() || Inventory.count(bar.getPrimaryOreId()) == 0;
    }

    /**
     * WALK_TO_DISPENSER state: walk to the bar dispenser.
     */
    private int handleWalkToDispenser() {
        // Brief wait for bars to smelt
        SleepUtils.tickSleep();
        SleepUtils.tickSleep();

        if (furnaceHandler.walkToDispenser()) {
            state = BotState.COLLECT_BARS;
        }
        return loopDelay();
    }

    /**
     * COLLECT_BARS state: collect smelted bars from the dispenser.
     */
    private int handleCollectBars() {
        BarType bar = config.getSelectedBar();

        // For gold: swap to ice gloves before collecting
        if (bar == BarType.GOLD && config.isUseIceGloves()) {
            furnaceHandler.equipIceGloves();
        }

        if (furnaceHandler.collectBars(bar)) {
            int barsCollected = Inventory.count(bar.getBarId());
            stats.addBarsSmelted(barsCollected);
            log("Collected " + barsCollected + " " + bar.getBarName() + "s");
            state = BotState.WALK_TO_BANK;
        } else {
            // Bars might not be ready yet, wait a tick
            state = BotState.WAITING;
        }
        return loopDelay();
    }

    /**
     * WAITING state: wait for bars to finish smelting.
     */
    private int handleWaiting() {
        SleepUtils.tickSleep();
        waitingForBars = true;

        // Try collecting again
        state = BotState.COLLECT_BARS;
        return loopDelay();
    }

    /**
     * WALK_TO_BANK state: walk back to bank to deposit bars and get more supplies.
     */
    private int handleWalkToBank() {
        if (furnaceHandler.walkToBank()) {
            state = BotState.BANKING;
        }
        return loopDelay();
    }

    @Override
    public void onPaint(Graphics g) {
        if (paint != null && stats != null) {
            paint.render((Graphics2D) g, state != null ? state : BotState.BANKING);
        }
    }

    @Override
    public void onExit() {
        if (stats != null) {
            log("=== Blast Furnace Bot Session Summary ===");
            log("Runtime: " + stats.getElapsedFormatted());
            log("Bars smelted: " + stats.getBarsSmelted() + " (" + stats.getBarsPerHour() + "/hr)");
            log("XP gained: " + (int) stats.getXpGained() + " (" + stats.getXpPerHour() + "/hr)");
            log("Trips made: " + stats.getTripsMade());
            log("Ore used: " + stats.getOreUsed());
            log("Coal used: " + stats.getCoalUsed());
        }
    }

    private int loopDelay() {
        return (int) (BotConfig.TICK_MS + Math.random() * 200);
    }
}
