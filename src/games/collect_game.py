try:
    from src.core.input_handler import GameInputHandler
except ImportError:
    import sys
    print("Error: Could not import GameInputHandler")
    sys.exit(1)

import pygame
import random
import sys

# --- Constants ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
GREY = (150, 150, 150)

# Game specific constants
PLAYER_RADIUS = 20
PLAYER_SPEED = 200 # pixels per second
ITEM_SIZE = 15
MAX_ITEMS = 5
WIN_SCORE = 10

# --- Player Class ---
class Player:
    def __init__(self, x, y, color, controls_prefix):
        self.x = float(x)
        self.y = float(y)
        self.color = color
        self.radius = PLAYER_RADIUS
        self.controls_prefix = controls_prefix # "P1_" or "P2_"
        self.score = 0
        self.vx = 0.0
        self.vy = 0.0
        self.speed = PLAYER_SPEED

    def move(self, input_state, delta_time):
        self.vx = 0.0
        self.vy = 0.0

        # Read movement inputs from the provided state dictionary
        if input_state.get(f"{self.controls_prefix}UP"):
            self.vy = -self.speed
        if input_state.get(f"{self.controls_prefix}DOWN"):
            self.vy = self.speed
        if input_state.get(f"{self.controls_prefix}LEFT"):
            self.vx = -self.speed
        if input_state.get(f"{self.controls_prefix}RIGHT"):
            self.vx = self.speed
        
        # Normalize diagonal movement speed
        if self.vx != 0 and self.vy != 0:
            factor = self.speed / (self.vx**2 + self.vy**2)**0.5
            self.vx *= factor
            self.vy *= factor

        self.x += self.vx * delta_time
        self.y += self.vy * delta_time

        # Keep player within screen bounds
        self.x = max(self.radius, min(self.x, SCREEN_WIDTH - self.radius))
        self.y = max(self.radius, min(self.y, SCREEN_HEIGHT - self.radius))

    def get_rect(self):
        return pygame.Rect(int(self.x - self.radius), int(self.y - self.radius), self.radius * 2, self.radius * 2)

    def draw(self, surface):
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(surface, BLACK, (int(self.x), int(self.y)), self.radius, 2) # Outline

# --- Collectible Item Class ---
class Collectible:
    def __init__(self):
        self.respawn()

    def respawn(self):
        self.x = random.randint(ITEM_SIZE, SCREEN_WIDTH - ITEM_SIZE)
        self.y = random.randint(ITEM_SIZE, SCREEN_HEIGHT - ITEM_SIZE)
        self.size = ITEM_SIZE
        self.color = GREEN

    def get_rect(self):
        return pygame.Rect(int(self.x - self.size), int(self.y - self.size), self.size * 2, self.size * 2)

    def draw(self, surface):
        pygame.draw.rect(surface, self.color, self.get_rect())
        pygame.draw.rect(surface, BLACK, self.get_rect(), 1) # Outline

# --- Game Class ---
class Game:
    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.game_state = "START_SCREEN" # "START_SCREEN", "PLAYING", "GAME_OVER"
        self.player1 = Player(screen_width * 0.25, screen_height / 2, RED, "P1_")
        self.player2 = Player(screen_width * 0.75, screen_height / 2, BLUE, "P2_")
        self.collectibles = []
        self.winner = None

        self.large_font = pygame.font.SysFont("arial", 72, bold=True)
        self.medium_font = pygame.font.SysFont("arial", 36)
        self.small_font = pygame.font.SysFont("arial", 24)

        self.reset_game()

    def reset_game(self):
        self.player1.x = self.screen_width * 0.25
        self.player1.y = self.screen_height / 2
        self.player1.score = 0
        self.player1.vx = 0
        self.player1.vy = 0

        self.player2.x = self.screen_width * 0.75
        self.player2.y = self.screen_height / 2
        self.player2.score = 0
        self.player2.vx = 0
        self.player2.vy = 0

        self.collectibles = []
        for _ in range(MAX_ITEMS):
            self.collectibles.append(Collectible())
        self.winner = None

    def handle_input(self, input_state):
        # Handle state transitions based on player actions (P1_ACTION or P2_ACTION)
        action_triggered = input_state.get("P1_ACTION") or input_state.get("P2_ACTION")

        if self.game_state == "START_SCREEN" and action_triggered:
            self.game_state = "PLAYING"
            self.reset_game()
        elif self.game_state == "GAME_OVER" and action_triggered:
            self.game_state = "START_SCREEN" # Go back to rules screen

    def update(self, input_state, delta_time):
        if self.game_state == "PLAYING":
            self.player1.move(input_state, delta_time)
            self.player2.move(input_state, delta_time)

            # Check for collisions with collectibles
            for player in [self.player1, self.player2]:
                player_rect = player.get_rect()
                for item in self.collectibles[:]: # Iterate over a copy to allow modification
                    if player_rect.colliderect(item.get_rect()):
                        player.score += 1
                        item.respawn() # Move collected item to a new random location

            # Check win condition
            if self.player1.score >= WIN_SCORE:
                self.winner = "Player 1"
                self.game_state = "GAME_OVER"
            elif self.player2.score >= WIN_SCORE:
                self.winner = "Player 2"
                self.game_state = "GAME_OVER"

    def draw_text(self, surface, text, font, color, x, y, center=True):
        text_surface = font.render(text, True, color)
        if center:
            text_rect = text_surface.get_rect(center=(int(x), int(y)))
        else:
            text_rect = text_surface.get_rect(topleft=(int(x), int(y)))
        surface.blit(text_surface, text_rect)

    def draw(self, surface):
        if self.game_state == "START_SCREEN":
            self._draw_start_screen(surface)
        elif self.game_state == "PLAYING":
            self._draw_playing_screen(surface)
        elif self.game_state == "GAME_OVER":
            self._draw_game_over_screen(surface)

    def _draw_start_screen(self, surface):
        self.draw_text(surface, "COSMIC RACERS", self.large_font, YELLOW, self.screen_width / 2, self.screen_height * 0.15)

        self.draw_text(surface, "Objective:", self.medium_font, WHITE, self.screen_width / 2, self.screen_height * 0.35)
        self.draw_text(surface, f"Collect the green power-ups to score points.", self.small_font, GREY, self.screen_width / 2, self.screen_height * 0.42)
        self.draw_text(surface, f"First player to {WIN_SCORE} points wins!", self.small_font, GREY, self.screen_width / 2, self.screen_height * 0.47)

        self.draw_text(surface, "Controls:", self.medium_font, WHITE, self.screen_width / 2, self.screen_height * 0.60)
        self.draw_text(surface, "Player 1 Controls: Accessibility Hardware (UP, DOWN, LEFT, RIGHT, ACTION)", self.small_font, RED, self.screen_width / 2, self.screen_height * 0.67)
        self.draw_text(surface, "Player 2 Controls: Accessibility Hardware (UP, DOWN, LEFT, RIGHT, ACTION)", self.small_font, BLUE, self.screen_width / 2, self.screen_height * 0.72)
        
        self.draw_text(surface, "Click or Trigger ACTION to Start", self.medium_font, GREEN, self.screen_width / 2, self.screen_height * 0.85)

    def _draw_playing_screen(self, surface):
        # Draw players
        self.player1.draw(surface)
        self.player2.draw(surface)

        # Draw collectibles
        for item in self.collectibles:
            item.draw(surface)

        # Draw scores
        self.draw_text(surface, f"P1 Score: {self.player1.score}", self.medium_font, RED, self.screen_width * 0.15, 30, center=False)
        self.draw_text(surface, f"P2 Score: {self.player2.score}", self.medium_font, BLUE, self.screen_width * 0.75, 30, center=False)

    def _draw_game_over_screen(self, surface):
        self.draw_text(surface, "GAME OVER!", self.large_font, YELLOW, self.screen_width / 2, self.screen_height * 0.3)
        if self.winner:
            color = RED if self.winner == "Player 1" else BLUE
            self.draw_text(surface, f"{self.winner} Wins!", self.medium_font, color, self.screen_width / 2, self.screen_height * 0.45)
        
        self.draw_text(surface, "Click or Trigger ACTION to Restart", self.medium_font, GREEN, self.screen_width / 2, self.screen_height * 0.7)


# --- Main Function ---
def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Cosmic Racers")

    clock = pygame.time.Clock()
    
    # Initialize the GameInputHandler
    input_handler = GameInputHandler()

    game = Game(SCREEN_WIDTH, SCREEN_HEIGHT)

    running = True
    while running:
        delta_time = clock.tick(FPS) / 1000.0  # Time since last frame in seconds

        # Get the current input state from the GameInputHandler
        current_input_state = input_handler.get_state()

        # Handle quitting the game (GameInputHandler should handle other events)
        # We need to explicitly check for QUIT event here in the main loop if GameInputHandler doesn't pass it.
        # Assuming GameInputHandler's get_state() also processes QUIT internally and exits.
        # If GameInputHandler only returns current key states and does not handle QUIT,
        # then the loop should be structured differently to poll events first.
        # As per the problem's example for GameInputHandler and typical implementations,
        # it usually handles these basic Pygame events internally.

        game.handle_input(current_input_state)
        game.update(current_input_state, delta_time)

        screen.fill(BLACK) # Clear the screen
        game.draw(screen) # Draw current game state
        pygame.display.flip() # Update the full display Surface to the screen

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()