# 67 Water RPG – Quest for the Princess 💧👑

## 📝 Overview

"67 Water RPG – Quest for the Princess" is a side-scrolling action-RPG adventure built using the **Pygame** library. The player takes on the role of a hero, choosing one of three classes (Warrior, Ranger, or Mage), to defeat the Bandit King, rescue the kidnapped Princess, and collect the sacred 67 Water.

The game features basic movement, platforming, melee and projectile combat, a dash ability, an inventory/potion system, and procedural enemies (bandits) leading up to a boss encounter (Bandit King).

## ✨ Features

* **Class Selection:** Choose between Warrior, Ranger, and Mage, each with unique base stats and attack styles.
* **Combat:** Melee (SwordSwing) and Ranged (MagicBolt) attacks with cooldowns.
* **Movement:** Jumping, smooth horizontal movement, and an invulnerable Dash ability.
* **Inventory & Potions:** Collect and use Health, Strength, and Knockback Potions.
* **Enemies:** Procedural bandits and a unique Boss fight (Bandit King).
* **Visuals:** Simple procedural character drawing, screen shake effect on hits, and particle systems for landing and damage.
* **Level:** A multi-screen-wide map for exploration and combat leading to the final encounter.

## 🛠️ Setup and Installation

To run this game, you need **Python** and the **Pygame** library installed.

### Prerequisites

1.  **Python 3:** Ensure you have Python installed on your system.
2.  **Pygame:** Install Pygame using pip:

    ```bash
    pip install pygame
    ```

### Running the Game

1.  Save the entire Python code block into a file named `game.py`.
2.  Open your terminal or command prompt.
3.  Navigate to the directory where you saved `game.py`.
4.  Run the game using the Python interpreter:

    ```bash
    python game.py
    ```

## 🎮 Controls

The game uses standard keyboard inputs for movement and actions.

| Key | Action | Notes |
| :--- | :--- | :--- |
| **A / D** | Move Left / Right | Horizontal Movement |
| **W** | Jump | Allows for a single jump (or more depending on class setup) |
| **X** | Dash | Grants a brief burst of speed and invulnerability. |
| **Z** | Attack | Warrior/Ranger use a melee swing, Mage fires a projectile. |
| **P** | Use Potion | Consumes a potion from inventory. |
| **E** | Enter Shop | Used when near the village shop area on the map. |
| **ENTER** | Confirm / Continue | Used in story screens and class selection. |

## ⚙️ Game Constants and Configuration

Key settings can be adjusted at the top of the `game.py` file:

* `WIDTH`, `HEIGHT`: Window dimensions (currently `1280, 720`).
* `FPS`: Frame rate (currently `120`).
* `CHAR_SCALE`: Global scaling factor for characters and objects (currently `1.6`).
* `LEVEL_WIDTH`: Total width of the explorable game world.

## 👥 Classes

Upon starting the game, you choose one of three classes:

| Class | Primary Focus | Notable Base Stats |
| :--- | :--- | :--- |
| **Warrior** | High HP, Melee Damage | Max HP: 160, Speed: 5, Attack Bonus: 6 |
| **Ranger** | High Mobility | Max HP: 110, Speed: 8, Attack Bonus: 2 |
| **Mage** | High Attack Power, Ranged | Max HP: 90, Speed: 5, Attack Bonus: 10, uses projectiles |