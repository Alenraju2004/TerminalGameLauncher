import pygame
import sys
import random

# CRITICAL: Do NOT use pygame.key.get_pressed() or standard event queues for player movement.
# You MUST read inputs from a dictionary returned by GameInputHandler.get_state().
# Player 1 moves using the boolean keys "P1_UP", "P1_DOWN", "P1_LEFT", "P1_RIGHT", and "P1_ACTION".
# Player 2 uses "P2_UP", etc. Structure the Pygame update loop to rely entirely on this state dictionary for velocity and actions.
try:
    from src.core.input_handler import GameInputHandler
except ImportError:
    print("Error: Could not import GameInputHandler.")
    sys.exit(1)

# Constants
# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)

# Screen dimensions
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600

# Game settings
FPS = 60
WINNING_SCORE = 5 # First to 5 tags wins

# Player Class
class Player:
    def __init__(self, x, y, color, player_num, name):
        self.x = float(x)
        self.y = float(y)
        self.color = color
        self.radius = 20
        self.speed = 5
        self.score = 0
        self.is_it = False
        self.player_num = player_num # 1 or 2
        self.name = name

    def update(self, input_state):
        dx, dy = 0, 0
        
        # Determine movement based on player number and input state
        if self.player_num == 1:
            if input_state["P1_UP"]: dy -= 1
            if input_state["P1_DOWN"]: dy += 1
            if input_state["P1_LEFT"]: dx -= 1
            if input_state["P1_RIGHT"]: dx += 1
        else: # Player 2
            if input_state["P2_UP"]: dy -= 1
            if input_state["P2_DOWN"]: dy += 1
            if input_state["P2_LEFT"]: dx -= 1
            if input_state["P2_RIGHT"]: dx += 1

        # Normalize diagonal movement speed
        if dx != 0 and dy != 0:
            speed_diag = self.speed * 0.707 # Approximation of 1/sqrt(2)
            self.x += dx * speed_diag
            self.y += dy * speed_diag
        else:
            self.x += dx * self.speed
            self.y += dy * self.speed

        # Keep player within screen bounds
        self.x = max(float(self.radius), min(self.x, float(SCREEN_WIDTH - self.radius)))
        self.y = max(float(self.radius), min(self.y, float(SCREEN_HEIGHT - self.radius)))

    def draw(self, screen, font):
        # Draw player circle
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.radius)
        
        # If player is 'it', draw a smaller inner circle to indicate status
        if self.is_it:
            pygame.draw.circle(screen, YELLOW, (int(self.x), int(self.y)), self.radius - 5, 2)
            it_text = font.render("IT!", True, YELLOW)
            text_rect = it_text.get_rect(center=(int(self.x), int(self.y - self.radius - it_text.get_height() // 2 - 5)))
            screen.blit(it_text, text_rect)

# Game Class
class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Pygame Tag")
        self.clock = pygame.time.Clock()

        # Initialize fonts for various text sizes
        self.font_large = pygame.font.SysFont("Arial", 72, bold=True)
        self.font_medium = pygame.font.SysFont("Arial", 36)
        self.font_small = pygame.font.SysFont("Arial", 24)

        # Create player instances
        self.player1 = Player(SCREEN_WIDTH // 4, SCREEN_HEIGHT // 2, RED, 1, "Player 1")
        self.player2 = Player(3 * SCREEN_WIDTH // 4, SCREEN_HEIGHT // 2, BLUE, 2, "Player 2")

        self.game_state = "START" # Initial game state
        self.winning_score = WINNING_SCORE
        self.winner = None
        
        # Variables for debouncing action inputs
        self.last_action_p1 = False
        self.last_action_p2 = False
        self.last_mouse_click = False

        self.reset_game()

    def reset_game(self):
        # Reset player positions, scores, and 'it' status
        self.player1.x = float(SCREEN_WIDTH // 4)
        self.player1.y = float(SCREEN_HEIGHT // 2)
        self.player1.score = 0
        self.player1.is_it = False

        self.player2.x = float(3 * SCREEN_WIDTH // 4)
        self.player2.y = float(SCREEN_HEIGHT // 2)
        self.player2.score = 0
        self.player2.is_it = False

        # Randomly decide who is 'it' at the start of a new round
        if random.choice([True, False]):
            self.player1.is_it = True
        else:
            self.player2.is_it = True
        
        self.winner = None
        self.game_state = "START" # Game always resets to the start screen

    def _check_collision(self, p1, p2):
        # Calculate distance between player centers
        distance_sq = (p1.x - p2.x)**2 + (p1.y - p2.y)**2
        # Check if distance is less than sum of radii (collision)
        return distance_sq <= (p1.radius + p2.radius)**2

    def _separate_players_after_tag(self, it_player, tagged_player):
        # Move players slightly apart to prevent instant re-tagging on collision
        dx = it_player.x - tagged_player.x
        dy = it_player.y - tagged_player.y
        dist = (dx**2 + dy**2)**0.5

        if dist == 0: # Handle case where players are exactly on top of each other
            dx, dy = 1, 0 # Default push direction
            dist = 1
        
        overlap = (it_player.radius + tagged_player.radius) - dist
        if overlap > 0:
            # Normalize vector and push apart by half the overlap distance for each player
            norm_dx = dx / dist
            norm_dy = dy / dist
            
            it_player.x += norm_dx * overlap / 2
            it_player.y += norm_dy * overlap / 2
            tagged_player.x -= norm_dx * overlap / 2
            tagged_player.y -= norm_dy * overlap / 2
            
            # Ensure players remain within screen bounds after separation
            it_player.x = max(float(it_player.radius), min(it_player.x, float(SCREEN_WIDTH - it_player.radius)))
            it_player.y = max(float(it_player.radius), min(it_player.y, float(SCREEN_HEIGHT - it_player.radius)))
            tagged_player.x = max(float(tagged_player.radius), min(tagged_player.x, float(SCREEN_WIDTH - tagged_player.radius)))
            tagged_player.y = max(float(tagged_player.radius), min(tagged_player.y, float(SCREEN_HEIGHT - tagged_player.radius)))

    def update_game_logic(self, input_state):
        self.player1.update(input_state) # Update player 1 position based on input
        self.player2.update(input_state) # Update player 2 position based on input

        if self._check_collision(self.player1, self.player2):
            if self.player1.is_it:
                self.player1.score += 1
                self.player1.is_it = False
                self.player2.is_it = True
                self._separate_players_after_tag(self.player1, self.player2) # Separate to prevent re-tag
            elif self.player2.is_it:
                self.player2.score += 1
                self.player2.is_it = False
                self.player1.is_it = True
                self._separate_players_after_tag(self.player2, self.player1) # Separate to prevent re-tag

        # Check for win condition
        if self.player1.score >= self.winning_score:
            self.winner = self.player1.name
            self.game_state = "GAMEOVER"
        elif self.player2.score >= self.winning_score:
            self.winner = self.player2.name
            self.game_state = "GAMEOVER"

    def draw_start_screen(self):
        self.screen.fill(BLACK)
        
        # Title
        title_text = self.font_large.render("TAG GAME", True, WHITE)
        self.screen.blit(title_text, (SCREEN_WIDTH // 2 - title_text.get_width() // 2, SCREEN_HEIGHT // 6))

        # Player 1 Controls
        controls_p1_title = self.font_medium.render("Player 1 Controls:", True, RED)
        self.screen.blit(controls_p1_title, (SCREEN_WIDTH // 2 - controls_p1_title.get_width() // 2, SCREEN_HEIGHT // 3))
        controls_p1_desc = self.font_small.render("Accessibility Hardware", True, WHITE)
        self.screen.blit(controls_p1_desc, (SCREEN_WIDTH // 2 - controls_p1_desc.get_width() // 2, SCREEN_HEIGHT // 3 + 40))

        # Player 2 Controls
        controls_p2_title = self.font_medium.render("Player 2 Controls:", True, BLUE)
        self.screen.blit(controls_p2_title, (SCREEN_WIDTH // 2 - controls_p2_title.get_width() // 2, SCREEN_HEIGHT // 2))
        controls_p2_desc = self.font_small.render("Accessibility Hardware", True, WHITE)
        self.screen.blit(controls_p2_desc, (SCREEN_WIDTH // 2 - controls_p2_desc.get_width() // 2, SCREEN_HEIGHT // 2 + 40))

        # Objective
        objective_text = self.font_medium.render(f"Objective: Be the first to tag your opponent {self.winning_score} times!", True, GREEN)
        self.screen.blit(objective_text, (SCREEN_WIDTH // 2 - objective_text.get_width() // 2, 3 * SCREEN_HEIGHT // 4 - 20))

        # Start Interaction prompt
        start_text = self.font_small.render("Click or Trigger ACTION to Start", True, YELLOW)
        self.screen.blit(start_text, (SCREEN_WIDTH // 2 - start_text.get_width() // 2, 3 * SCREEN_HEIGHT // 4 + 50))

    def draw_play_screen(self):
        self.screen.fill(BLACK)

        # Draw players
        self.player1.draw(self.screen, self.font_small)
        self.player2.draw(self.screen, self.font_small)

        # Draw scores
        score_p1_text = self.font_medium.render(f"{self.player1.name}: {self.player1.score}", True, self.player1.color)
        score_p2_text = self.font_medium.render(f"{self.player2.name}: {self.player2.score}", True, self.player2.color)
        
        self.screen.blit(score_p1_text, (20, 20))
        self.screen.blit(score_p2_text, (SCREEN_WIDTH - score_p2_text.get_width() - 20, 20))

    def draw_game_over_screen(self):
        self.screen.fill(BLACK)
        
        # Game Over title
        game_over_text = self.font_large.render("GAME OVER", True, WHITE)
        self.screen.blit(game_over_text, (SCREEN_WIDTH // 2 - game_over_text.get_width() // 2, SCREEN_HEIGHT // 3))

        # Winner announcement
        winner_text = self.font_medium.render(f"{self.winner} Wins!", True, GREEN)
        self.screen.blit(winner_text, (SCREEN_WIDTH // 2 - winner_text.get_width() // 2, SCREEN_HEIGHT // 2))

        # Restart Interaction prompt
        restart_text = self.font_small.render("Click or Trigger ACTION to Restart", True, YELLOW)
        self.screen.blit(restart_text, (SCREEN_WIDTH // 2 - restart_text.get_width() // 2, 2 * SCREEN_HEIGHT // 3))

    def run(self, game_input_handler):
        running = True
        while running:
            current_input_state = game_input_handler.get_state()
            mouse_buttons = pygame.mouse.get_pressed() # Check mouse buttons directly for click detection

            # Debounce action inputs (only trigger on the "rising edge" of a press)
            p1_action_just_pressed = current_input_state["P1_ACTION"] and not self.last_action_p1
            p2_action_just_pressed = current_input_state["P2_ACTION"] and not self.last_action_p2
            mouse_just_clicked = mouse_buttons[0] and not self.last_mouse_click # Left mouse button

            # Event handling for quitting the game
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            # State machine logic
            if self.game_state == "START":
                # Transition to PLAY state on any action input
                if p1_action_just_pressed or p2_action_just_pressed or mouse_just_clicked:
                    self.game_state = "PLAY"
            elif self.game_state == "PLAY":
                self.update_game_logic(current_input_state)
            elif self.game_state == "GAMEOVER":
                # Transition back to START state on any action input
                if p1_action_just_pressed or p2_action_just_pressed or mouse_just_clicked:
                    self.reset_game() # Reset all game elements
                    # game_state is set to "START" within reset_game()

            # Drawing based on current game state
            if self.game_state == "START":
                self.draw_start_screen()
            elif self.game_state == "PLAY":
                self.draw_play_screen()
            elif self.game_state == "GAMEOVER":
                self.draw_game_over_screen()

            pygame.display.flip() # Update the full display Surface to the screen
            self.clock.tick(FPS) # Cap the frame rate

            # Update last action states for next frame's debouncing
            self.last_action_p1 = current_input_state["P1_ACTION"]
            self.last_action_p2 = current_input_state["P2_ACTION"]
            self.last_mouse_click = mouse_buttons[0]

        pygame.quit()
        sys.exit()

# Main execution block
if __name__ == "__main__":
    game_input_handler_instance = GameInputHandler()
    game = Game()
    game.run(game_input_handler_instance)