package com.blastfurnace.core;

/**
 * Configuration for the Blast Furnace bot session.
 */
public class BotConfig {

    // Item IDs
    public static final int COAL_BAG_ID = 12019;
    public static final int COAL_BAG_OPEN_ID = 24480;
    public static final int COAL_ID = 453;
    public static final int ICE_GLOVES_ID = 1580;
    public static final int GOLDSMITH_GAUNTLETS_ID = 776;
    public static final int SMITHS_GLOVES_I_ID = 25107;
    public static final int STAMINA_POTION_1_ID = 12631;
    public static final int STAMINA_POTION_2_ID = 12629;
    public static final int STAMINA_POTION_3_ID = 12627;
    public static final int STAMINA_POTION_4_ID = 12625;
    public static final int COINS_ID = 995;
    public static final int BUCKET_OF_WATER_ID = 1929;

    // Game object IDs
    public static final int CONVEYOR_BELT_ID = 9100;
    public static final int BAR_DISPENSER_ID = 9092;
    public static final int BANK_CHEST_ID = 26707;
    public static final int COFFER_ID = 29330;

    // Widget IDs
    public static final int BAR_DISPENSER_WIDGET_PARENT = 270;
    public static final int BAR_DISPENSER_WIDGET_CHILD = 14;

    // Varbits
    public static final int COFFER_VARBIT = 5357;
    public static final int COAL_IN_FURNACE_VARBIT = 5340;
    public static final int STAMINA_EFFECT_VARBIT = 25;

    // Areas (approximate tile coordinates)
    public static final int BANK_AREA_X_MIN = 1948;
    public static final int BANK_AREA_X_MAX = 1950;
    public static final int BANK_AREA_Y_MIN = 4956;
    public static final int BANK_AREA_Y_MAX = 4968;
    public static final int CONVEYOR_TILE_X = 1942;
    public static final int CONVEYOR_TILE_Y = 4967;
    public static final int DISPENSER_TILE_X = 1940;
    public static final int DISPENSER_TILE_Y = 4963;

    // Thresholds
    public static final int COFFER_MIN_AMOUNT = 10000;
    public static final int COFFER_REFILL_AMOUNT = 60000;
    public static final int STAMINA_THRESHOLD = 30;
    public static final int MAX_COAL_IN_FURNACE = 254;

    // Timing (ms)
    public static final int TICK_MS = 600;
    public static final int ACTION_DELAY_MIN = 150;
    public static final int ACTION_DELAY_MAX = 400;
    public static final int WALK_TIMEOUT = 8000;
    public static final int INTERACTION_TIMEOUT = 5000;

    // Session config (set by GUI)
    private BarType selectedBar = BarType.GOLD;
    private boolean useGoldsmithGauntlets = true;
    private boolean useCoalBag = true;
    private boolean useStaminaPotions = true;
    private boolean useIceGloves = true;
    private int coalBagSlot = 0;
    private boolean hybridMode = false;
    private BarType hybridBar = null;

    public BarType getSelectedBar() { return selectedBar; }
    public void setSelectedBar(BarType bar) { this.selectedBar = bar; }

    public boolean isUseGoldsmithGauntlets() { return useGoldsmithGauntlets; }
    public void setUseGoldsmithGauntlets(boolean v) { this.useGoldsmithGauntlets = v; }

    public boolean isUseCoalBag() { return useCoalBag; }
    public void setUseCoalBag(boolean v) { this.useCoalBag = v; }

    public boolean isUseStaminaPotions() { return useStaminaPotions; }
    public void setUseStaminaPotions(boolean v) { this.useStaminaPotions = v; }

    public boolean isUseIceGloves() { return useIceGloves; }
    public void setUseIceGloves(boolean v) { this.useIceGloves = v; }

    public int getCoalBagSlot() { return coalBagSlot; }
    public void setCoalBagSlot(int slot) { this.coalBagSlot = slot; }

    public boolean isHybridMode() { return hybridMode; }
    public void setHybridMode(boolean v) { this.hybridMode = v; }

    public BarType getHybridBar() { return hybridBar; }
    public void setHybridBar(BarType bar) { this.hybridBar = bar; }

    /**
     * Whether the current bar selection needs coal.
     */
    public boolean needsCoal() {
        return selectedBar.requiresCoal();
    }

    /**
     * Whether we need ice gloves for the current bar.
     * All bars except gold (which uses goldsmith gauntlets) benefit from ice gloves.
     */
    public boolean needsIceGloves() {
        return useIceGloves && selectedBar != BarType.GOLD;
    }
}
