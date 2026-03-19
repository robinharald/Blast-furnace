package com.blastfurnace.core;

/**
 * All bar types available at the Blast Furnace.
 * Coal requirements are already halved (Blast Furnace perk).
 */
public enum BarType {

    BRONZE("Bronze bar", "Copper ore", "Tin ore", 2349, 436, 438, 0, 1, false),
    IRON("Iron bar", "Iron ore", null, 2351, 440, -1, 0, 15, false),
    SILVER("Silver bar", "Silver ore", null, 2355, 442, -1, 0, 20, false),
    STEEL("Steel bar", "Iron ore", null, 2353, 440, -1, 1, 30, true),
    GOLD("Gold bar", "Gold ore", null, 2357, 444, -1, 0, 40, false),
    MITHRIL("Mithril bar", "Mithril ore", null, 2359, 447, -1, 2, 50, true),
    ADAMANTITE("Adamantite bar", "Adamantite ore", null, 2361, 449, -1, 3, 70, true),
    RUNITE("Runite bar", "Runite ore", null, 2363, 451, -1, 4, 85, true);

    private final String barName;
    private final String primaryOreName;
    private final String secondaryOreName;
    private final int barId;
    private final int primaryOreId;
    private final int secondaryOreId;
    private final int coalPerBar;
    private final int smithingLevel;
    private final boolean requiresCoal;

    BarType(String barName, String primaryOreName, String secondaryOreName,
            int barId, int primaryOreId, int secondaryOreId,
            int coalPerBar, int smithingLevel, boolean requiresCoal) {
        this.barName = barName;
        this.primaryOreName = primaryOreName;
        this.secondaryOreName = secondaryOreName;
        this.barId = barId;
        this.primaryOreId = primaryOreId;
        this.secondaryOreId = secondaryOreId;
        this.coalPerBar = coalPerBar;
        this.smithingLevel = smithingLevel;
        this.requiresCoal = requiresCoal;
    }

    public String getBarName() { return barName; }
    public String getPrimaryOreName() { return primaryOreName; }
    public String getSecondaryOreName() { return secondaryOreName; }
    public int getBarId() { return barId; }
    public int getPrimaryOreId() { return primaryOreId; }
    public int getSecondaryOreId() { return secondaryOreId; }
    public int getCoalPerBar() { return coalPerBar; }
    public int getSmithingLevel() { return smithingLevel; }
    public boolean requiresCoal() { return requiresCoal; }
    public boolean hasTwoOres() { return secondaryOreId != -1; }

    /**
     * For bars that require coal, calculate how many coal-only trips
     * are needed per ore trip when using the coal bag (27 capacity).
     * Returns 0 for non-coal bars.
     */
    public int getCoalTripsPerOreTrip() {
        if (!requiresCoal) return 0;
        // With coal bag (27) + inventory coal, we calculate the ratio
        // Steel: 1 coal per bar, 27 bars per trip -> 1 coal bag trip covers it
        // Mithril: 2 coal per bar, 27 ore -> need 54 coal -> 2 coal bag fills
        // Adamantite: 3 coal per bar, 27 ore -> need 81 coal -> 3 coal bag fills
        // Runite: 4 coal per bar, 27 ore -> need 108 coal -> 4 coal bag fills
        return coalPerBar;
    }

    /**
     * How many ore can we carry per trip (inventory minus coal bag slot).
     * Coal bag takes 1 slot. For two-ore bars (bronze), each ore takes space.
     */
    public int getOrePerTrip() {
        if (hasTwoOres()) {
            // Bronze: 13 copper + 13 tin + 1 coal bag slot = 27
            return 13;
        }
        // 27 slots for ore (1 slot reserved for coal bag)
        return 27;
    }

    /**
     * Smithing XP per bar smelted.
     */
    public double getXpPerBar() {
        switch (this) {
            case BRONZE: return 6.2;
            case IRON: return 12.5;
            case SILVER: return 13.7;
            case STEEL: return 17.5;
            case GOLD: return 22.5; // 56.2 with goldsmith gauntlets
            case MITHRIL: return 30.0;
            case ADAMANTITE: return 37.5;
            case RUNITE: return 50.0;
            default: return 0;
        }
    }

    /**
     * Gold XP with goldsmith gauntlets.
     */
    public double getGoldsmithXp() {
        return this == GOLD ? 56.2 : getXpPerBar();
    }

    @Override
    public String toString() {
        return barName;
    }
}
