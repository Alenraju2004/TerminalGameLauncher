try:
    from src.core.input_handler import GameInputHandler
except ImportError:
    import sys
    print("Error: Could not import GameInputHandler.")
    sys.exit(1)

import pygame
import sys
import random
import math

# --- Constants ---
# Screen dimensions
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600

# Colors (R, G, B)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
GRAY = (100, 100, 100)
LIGHTGRAY = (200, 200, 200)
DARKGRAY = (50, 50, 50)
YELLOW = (255, 255, 0)
ORANGE = (255, 165, 0)

BACKGROUND_COLOR = DARKGRAY
TEXT_COLOR = WHITE
PLAYER_COLOR_1 = BLUE
PLAYER_COLOR_2 = RED
TRACK_COLOR = GRAY
WALL_COLOR = BLACK # Areas players cannot enter
CHECKPOINT_COLOR = GREEN

# Game settings
FPS = 60
WIN_LAPS = 3 # Number of laps to win

# --- Player Class ---
class Player:
    def __init__(self, start_pos, color, player_prefix, track_walls, checkpoints):
        self.x, self.y = float(start_pos[0]), float(start_pos[1])
        self.color = color
        self.player_prefix = player_prefix # e.g., "P1", "P2"
        self.width = 20
        self.height = 20
        self.rect = pygame.Rect(int(self.x - self.width // 2), int(self.y - self.height // 2), self.width, self.height)
        self.vel_x = 0.0
        self.vel_y = 0.0
        self.acceleration_rate = 0.25 # How fast player accelerates
        self.max_speed = 5.0
        self.friction = 0.95 # Damping factor for speed

        self.laps = 0
        self.current_checkpoint = 0 # Index of the next checkpoint to hit
        self.last_checkpoint_hit_time = 0 # To prevent hitting same checkpoint multiple times rapidly
        self.checkpoints = checkpoints
        self.track_walls = track_walls # For collision detection

    def move(self, input_state):
        # Update velocity based on input
        if input_state.get(self.player_prefix + "_UP"):
            self.vel_y -= self.acceleration_rate
        if input_state.get(self.player_prefix + "_DOWN"):
            self.vel_y += self.acceleration_rate
        if input_state.get(self.player_prefix + "_LEFT"):
            self.vel_x -= self.acceleration_rate
        if input_state.get(self.player_prefix + "_RIGHT"):
            self.vel_x += self.acceleration_rate

        # Apply max speed limit
        current_speed = (self.vel_x**2 + self.vel_y**2)**0.5
        if current_speed > self.max_speed:
            if current_speed != 0: # Avoid division by zero
                self.vel_x = (self.vel_x / current_speed) * self.max_speed
                self.vel_y = (self.vel_y / current_speed) * self.max_speed

        # Apply friction
        self.vel_x *= self.friction
        self.vel_y *= self.friction

        # Update position
        new_x = self.x + self.vel_x
        new_y = self.y + self.vel_y

        # Collision detection with walls
        # Check X movement
        test_rect_x = pygame.Rect(int(new_x - self.width // 2), int(self.y - self.height // 2), self.width, self.height)
        for wall in self.track_walls:
            if test_rect_x.colliderect(wall):
                new_x = self.x # Revert X position
                self.vel_x = 0 # Stop horizontal movement
                break

        # Check Y movement
        test_rect_y = pygame.Rect(int(self.x - self.width // 2), int(new_y - self.height // 2), self.width, self.height)
        for wall in self.track_walls:
            if test_rect_y.colliderect(wall):
                new_y = self.y # Revert Y position
                self.vel_y = 0 # Stop vertical movement
                break
        
        self.x = new_x
        self.y = new_y
        self.rect.center = (int(self.x), int(self.y))

        self._check_checkpoints()

    def _check_checkpoints(self):
        if not self.checkpoints:
            return

        current_time = pygame.time.get_ticks()
        debounce_time = 500 # ms to prevent multiple hits on same checkpoint

        # Index of the NEXT checkpoint the player needs to hit
        if self.current_checkpoint < len(self.checkpoints):
            target_checkpoint_rect = self.checkpoints[self.current_checkpoint].rect
        else:
            # This case should ideally not be hit if logic is robust, but for safety
            target_checkpoint_rect = self.checkpoints[0].rect 

        if self.rect.colliderect(target_checkpoint_rect):
            if current_time - self.last_checkpoint_hit_time > debounce_time:
                self.current_checkpoint += 1
                self.last_checkpoint_hit_time = current_time

                # If all checkpoints for the lap are hit
                if self.current_checkpoint >= len(self.checkpoints):
                    self.laps += 1
                    self.current_checkpoint = 0 # Reset to hit CP0 next for the new lap

    def draw(self, screen):
        # Draw the player (car) as a filled rectangle
        pygame.draw.rect(screen, self.color, self.rect)
        # Draw a border
        pygame.draw.rect(screen, BLACK, self.rect, 2)
        
        # Draw a direction indicator
        indicator_length = 15
        indicator_thickness = 3
        center_x, center_y = self.rect.center
        
        angle = 0 # Default angle (right)
        if self.vel_x != 0 or self.vel_y != 0:
            angle = math.atan2(self.vel_y, self.vel_x)
        
        end_x = int(center_x + indicator_length * math.cos(angle))
        end_y = int(center_y + indicator_length * math.sin(angle))
        pygame.draw.line(screen, WHITE, (int(center_x), int(center_y)), (end_x, end_y), indicator_thickness)


# --- Track Elements ---
class Checkpoint:
    def __init__(self, x, y, width, height, color):
        self.rect = pygame.Rect(int(x), int(y), int(width), int(height))
        self.color = color

class Track:
    def __init__(self):
        track_boundary_thickness = 50
        inner_island_thickness = 100

        self.walls = []
        # Outer boundary walls
        self.walls.append(pygame.Rect(0, 0, SCREEN_WIDTH, track_boundary_thickness)) # Top
        self.walls.append(pygame.Rect(0, SCREEN_HEIGHT - track_boundary_thickness, SCREEN_WIDTH, track_boundary_thickness)) # Bottom
        self.walls.append(pygame.Rect(0, track_boundary_thickness, track_boundary_thickness, SCREEN_HEIGHT - 2 * track_boundary_thickness)) # Left
        self.walls.append(pygame.Rect(SCREEN_WIDTH - track_boundary_thickness, track_boundary_thickness, track_boundary_thickness, SCREEN_HEIGHT - 2 * track_boundary_thickness)) # Right

        # Inner island wall (a large central rectangle)
        self.inner_island = pygame.Rect(
            track_boundary_thickness + inner_island_thickness,
            track_boundary_thickness + inner_island_thickness,
            SCREEN_WIDTH - 2 * (track_boundary_thickness + inner_island_thickness),
            SCREEN_HEIGHT - 2 * (track_boundary_thickness + inner_island_thickness)
        )
        self.walls.append(self.inner_island)

        # Checkpoints - defined for a clockwise race
        checkpoint_width = 40
        checkpoint_height = 40
        
        # CP0: Top-Left of inner track (Start/Finish Line)
        # CP1: Top-Right of inner track
        # CP2: Bottom-Right of inner track
        # CP3: Bottom-Left of inner track
        self.checkpoints = [
            Checkpoint(self.inner_island.left - 40, self.inner_island.top + 20, checkpoint_width, checkpoint_height, CHECKPOINT_COLOR), 
            Checkpoint(self.inner_island.right + 20, self.inner_island.top + 20, checkpoint_width, checkpoint_height, CHECKPOINT_COLOR),
            Checkpoint(self.inner_island.right + 20, self.inner_island.bottom - 60, checkpoint_width, checkpoint_height, CHECKPOINT_COLOR),
            Checkpoint(self.inner_island.left - 40, self.inner_island.bottom - 60, checkpoint_width, checkpoint_height, CHECKPOINT_COLOR)
        ]

    def draw(self, screen, player1_current_cp_idx, player2_current_cp_idx):
        # Draw background (track area)
        pygame.draw.rect(screen, TRACK_COLOR, (0, 0, SCREEN_WIDTH, SCREEN_HEIGHT))

        # Draw walls (these are the forbidden areas)
        for wall in self.walls:
            pygame.draw.rect(screen, WALL_COLOR, wall)

        # Draw checkpoints and highlight current ones
        for i, cp in enumerate(self.checkpoints):
            # Base checkpoint color
            pygame.draw.rect(screen, cp.color, cp.rect, 0)
            
            # Highlight border if it's the current target for a player
            if i == player1_current_cp_idx:
                pygame.draw.rect(screen, PLAYER_COLOR_1, cp.rect, 3) 
            if i == player2_current_cp_idx:
                pygame.draw.rect(screen, PLAYER_COLOR_2, cp.rect, 3)
            
            # Draw checkpoint number
            font = pygame.font.SysFont("Arial", 16)
            text = font.render(str(i), True, BLACK) # Checkpoint indices start from 0
            text_rect = text.get_rect(center=cp.rect.center)
            screen.blit(text, text_rect)


# --- Game Class ---
class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Galactic Race")
        self.clock = pygame.time.Clock()
        self.game_state = "RULES" # Initial state
        self.game_input_handler = None # Will be set by main()

        # Fonts
        self.title_font = pygame.font.SysFont("Arial", 72, True)
        self.header_font = pygame.font.SysFont("Arial", 48, True)
        self.text_font = pygame.font.SysFont("Arial", 28)
        self.small_text_font = pygame.font.SysFont("Arial", 20)
        self.bold_text_font = pygame.font.SysFont("Arial", 28, True)

        self.track = Track()
        
        # Player start positions, calculated relative to track's first checkpoint
        start_cp_center_x = self.track.checkpoints[0].rect.centerx
        start_cp_center_y = self.track.checkpoints[0].rect.centery
        
        player1_start = (start_cp_center_x, start_cp_center_y - 20)
        player2_start = (start_cp_center_x, start_cp_center_y + 20)

        self.player1 = Player(player1_start, PLAYER_COLOR_1, "P1", self.track.walls, self.track.checkpoints)
        self.player2 = Player(player2_start, PLAYER_COLOR_2, "P2", self.track.walls, self.track.checkpoints)
        self.players = [self.player1, self.player2]

        self.winner = None

    def reset_game(self):
        # Reset players to initial state and position
        start_cp_center_x = self.track.checkpoints[0].rect.centerx
        start_cp_center_y = self.track.checkpoints[0].rect.centery
        player1_start = (start_cp_center_x, start_cp_center_y - 20)
        player2_start = (start_cp_center_x, start_cp_center_y + 20)

        self.player1 = Player(player1_start, PLAYER_COLOR_1, "P1", self.track.walls, self.track.checkpoints)
        self.player2 = Player(player2_start, PLAYER_COLOR_2, "P2", self.track.walls, self.track.checkpoints)
        self.players = [self.player1, self.player2]
        self.winner = None
        self.game_state = "RULES" # After reset, go back to rules screen

    def _get_restart_rect(self):
        # Helper to get the bounding box for the "Restart" button for click detection
        text = self.bold_text_font.render("RESTART", True, TEXT_COLOR)
        return text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 100))

    def run(self, game_input_handler_instance):
        self.game_input_handler = game_input_handler_instance
        running = True
        while running:
            input_state = self.game_input_handler.get_state()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if self.game_state == "RULES":
                        self.game_state = "PLAY"
                    elif self.game_state == "GAMEOVER":
                        restart_rect = self._get_restart_rect()
                        if restart_rect.collidepoint(event.pos):
                            self.reset_game()

            # Handle P1/P2_ACTION for state transitions (for "Accessibility Hardware")
            if self.game_state == "RULES":
                if input_state.get("P1_ACTION") or input_state.get("P2_ACTION"):
                    self.game_state = "PLAY"
            elif self.game_state == "GAMEOVER":
                if input_state.get("P1_ACTION") or input_state.get("P2_ACTION"):
                    self.reset_game()

            self.screen.fill(BACKGROUND_COLOR)

            if self.game_state == "RULES":
                self._draw_rules_screen()
            elif self.game_state == "PLAY":
                self._update_game_play(input_state)
                self._draw_game_play()
            elif self.game_state == "GAMEOVER":
                self._draw_game_over_screen()

            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()
        sys.exit()

    def _update_game_play(self, input_state):
        for player in self.players:
            player.move(input_state)
            if player.laps >= WIN_LAPS:
                self.winner = player
                self.game_state = "GAMEOVER"
                break # A winner has been determined, stop updating and go to game over

    def _draw_rules_screen(self):
        title_text = self.title_font.render("Galactic Race", True, YELLOW)
        title_rect = title_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 4))
        self.screen.blit(title_text, title_rect)

        controls_title = self.header_font.render("Controls:", True, TEXT_COLOR)
        controls_rect = controls_title.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 80))
        self.screen.blit(controls_title, controls_rect)

        p1_controls = self.text_font.render("Player 1 Controls: Accessibility Hardware", True, PLAYER_COLOR_1)
        p1_rect = p1_controls.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 30))
        self.screen.blit(p1_controls, p1_rect)

        p2_controls = self.text_font.render("Player 2 Controls: Accessibility Hardware", True, PLAYER_COLOR_2)
        p2_rect = p2_controls.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 10))
        self.screen.blit(p2_controls, p2_rect)

        objective_text = self.text_font.render(f"Objective: Be the first racer to complete {WIN_LAPS} laps to win!", True, TEXT_COLOR)
        objective_rect = objective_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 80))
        self.screen.blit(objective_text, objective_rect)
        
        objective_text2 = self.small_text_font.render("Navigate the track and hit checkpoints (0, 1, 2, 3) in order.", True, TEXT_COLOR)
        objective_rect2 = objective_text2.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 110))
        self.screen.blit(objective_text2, objective_rect2)

        start_text = self.bold_text_font.render("Click or Trigger ACTION to Start", True, GREEN)
        start_rect = start_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 100))
        self.screen.blit(start_text, start_rect)

    def _draw_game_play(self):
        # Draw track walls and checkpoints
        p1_current_cp = self.player1.current_checkpoint % len(self.track.checkpoints) if self.track.checkpoints else 0
        p2_current_cp = self.player2.current_checkpoint % len(self.track.checkpoints) if self.track.checkpoints else 0
        self.track.draw(self.screen, p1_current_cp, p2_current_cp)

        # Draw players
        for player in self.players:
            player.draw(self.screen)

        # Display scores/laps
        p1_score_text = self.text_font.render(f"P1 Laps: {self.player1.laps}/{WIN_LAPS} Next CP: {self.player1.current_checkpoint}", True, PLAYER_COLOR_1)
        self.screen.blit(p1_score_text, (10, 10))
        
        p2_score_text = self.text_font.render(f"P2 Laps: {self.player2.laps}/{WIN_LAPS} Next CP: {self.player2.current_checkpoint}", True, PLAYER_COLOR_2)
        p2_score_rect = p2_score_text.get_rect(topright=(SCREEN_WIDTH - 10, 10))
        self.screen.blit(p2_score_text, p2_score_rect)

    def _draw_game_over_screen(self):
        game_over_text = self.header_font.render("GAME OVER", True, RED)
        game_over_rect = game_over_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 80))
        self.screen.blit(game_over_text, game_over_rect)

        if self.winner:
            winner_message = self.title_font.render(f"{self.winner.player_prefix} WINS!", True, self.winner.color)
            winner_rect = winner_message.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
            self.screen.blit(winner_message, winner_rect)

        restart_text = self.bold_text_font.render("RESTART", True, GREEN)
        restart_rect = self._get_restart_rect()
        pygame.draw.rect(self.screen, DARKGRAY, restart_rect.inflate(20, 10)) # Background for button
        pygame.draw.rect(self.screen, GREEN, restart_rect.inflate(20, 10), 3) # Border
        self.screen.blit(restart_text, restart_rect)


# --- Main Function ---
def main():
    game_input_handler = GameInputHandler() # Create instance of GameInputHandler
    game = Game()
    game.run(game_input_handler) # Pass the input handler instance to the game


if __name__ == "__main__":
    main()