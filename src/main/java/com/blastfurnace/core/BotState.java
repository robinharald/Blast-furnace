package com.blastfurnace.core;

/**
 * States for the Blast Furnace bot state machine.
 */
public enum BotState {
    BANKING("Banking"),
    FILL_COAL_BAG("Filling coal bag"),
    WALK_TO_CONVEYOR("Walking to conveyor"),
    DEPOSIT_COAL("Depositing coal on conveyor"),
    DEPOSIT_ORE("Depositing ore on conveyor"),
    WALK_TO_DISPENSER("Walking to bar dispenser"),
    COLLECT_BARS("Collecting bars"),
    WALK_TO_BANK("Walking to bank"),
    REFILL_COFFER("Refilling coffer"),
    EQUIP_GLOVES("Equipping gloves"),
    WAITING("Waiting for bars"),
    STOPPED("Stopped");

    private final String description;

    BotState(String description) {
        this.description = description;
    }

    public String getDescription() { return description; }

    @Override
    public String toString() { return description; }
}
