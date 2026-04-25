import pygame
import random
import sys

try:
    from src.core.input_handler import GameInputHandler
except ImportError:
    print("Error: Could not import GameInputHandler.")
    sys.exit(1)

# Initialize Pygame
pygame.init()

# Screen dimensions
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
SCREEN = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Pygame Racing!")

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
GRAY = (100, 100, 100)
LIGHT_GRAY = (200, 200, 200)

# Fonts
FONT_LARGE = pygame.font.SysFont("Arial", 64, bold=True)
FONT_MEDIUM = pygame.font.SysFont("Arial", 36)
FONT_SMALL = pygame.font.SysFont("Arial", 24)
FONT_TINY = pygame.font.SysFont("Arial", 18)

class Player:
    def __init__(self, x, y, color, controls, player_id):
        self.x = float(x)
        self.y = float(y)
        self.width = 30
        self.height = 40
        self.color = color
        self.speed = 3.5
        self.controls = controls
        self.player_id = player_id
        self.score = 0
        self.direction = 0  # 0: up, 1: right, 2: down, 3: left
        self.rotation_speed = 3 # Degrees per frame
        self.velocity = [0.0, 0.0]
        self.max_velocity = 5.0
        self.acceleration = 0.1
        self.friction = 0.97

    def rotate(self, angle_degrees):
        self.direction = (self.direction + angle_degrees) % 360

    def accelerate(self):
        angle_rad = pygame.math.Vector2(0, -1).rotate(self.direction).as_polar()[1]
        self.velocity[0] += self.acceleration * pygame.math.Vector2(0, -1).rotate(self.direction).x
        self.velocity[1] += self.acceleration * pygame.math.Vector2(0, -1).rotate(self.direction).y
        
        # Limit max velocity
        current_speed = pygame.math.Vector2(self.velocity).length()
        if current_speed > self.max_velocity:
            self.velocity = pygame.math.Vector2(self.velocity).normalize() * self.max_velocity
            
    def update(self, state):
        # Apply friction
        self.velocity[0] *= self.friction
        self.velocity[1] *= self.friction

        # Handle movement input using GameInputHandler states
        if state.get(self.controls['up']):
            self.accelerate()
        if state.get(self.controls['left']):
            self.rotate(-self.rotation_speed)
        if state.get(self.controls['right']):
            self.rotate(self.rotation_speed)

        self.x += self.velocity[0]
        self.y += self.velocity[1]

        # Keep player on screen
        self.x = max(self.width / 2, min(SCREEN_WIDTH - self.width / 2, self.x))
        self.y = max(self.height / 2, min(SCREEN_HEIGHT - self.height / 2, self.y))

    def draw(self, screen):
        # Draw the car body
        center_x, center_y = int(self.x), int(self.y)
        points = [
            pygame.math.Vector2(0, -self.height / 2),  # Top point
            pygame.math.Vector2(self.width / 2, self.height / 2),  # Bottom right
            pygame.math.Vector2(-self.width / 2, self.height / 2)   # Bottom left
        ]
        
        rotated_points = []
        for point in points:
            rotated_point = point.rotate(self.direction)
            rotated_points.append((rotated_point.x + center_x, rotated_point.y + center_y))

        pygame.draw.polygon(screen, self.color, rotated_points)
        pygame.draw.polygon(screen, BLACK, rotated_points, 2) # Outline

        # Draw a "headlight" to show direction
        headlight_offset = pygame.math.Vector2(0, -self.height / 2 - 5).rotate(self.direction)
        pygame.draw.circle(screen, YELLOW, (int(self.x + headlight_offset.x), int(self.y + headlight_offset.y)), 3)

    def get_rect(self):
        # Approximate bounding box for collision detection
        return pygame.Rect(int(self.x - self.width / 2), int(self.y - self.height / 2), self.width, self.height)

class Checkpoint:
    def __init__(self, x, y, radius, color):
        self.x = float(x)
        self.y = float(y)
        self.radius = radius
        self.color = color
        self.is_active = True

    def draw(self, screen):
        if self.is_active:
            pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.radius, 0)
            pygame.draw.circle(screen, BLACK, (int(self.x), int(self.y)), self.radius, 2)
        else:
            pygame.draw.circle(screen, LIGHT_GRAY, (int(self.x), int(self.y)), self.radius, 0)
            pygame.draw.circle(screen, BLACK, (int(self.x), int(self.y)), self.radius, 2)

    def check_collision(self, player_rect):
        dist_sq = (player_rect.centerx - self.x)**2 + (player_rect.centery - self.y)**2
        return dist_sq < (self.radius + min(player_rect.width, player_rect.height) / 2)**2 and self.is_active

class Game:
    def __init__(self):
        self.game_state = "START"
        
        # Instantiate UDP Input hook natively
        self.input_handler = GameInputHandler()
        
        self.player1 = Player(150, SCREEN_HEIGHT / 2, BLUE,
                              {'up': 'P1_UP', 'left': 'P1_LEFT', 'right': 'P1_RIGHT'}, 1)
        self.player2 = Player(SCREEN_WIDTH - 150, SCREEN_HEIGHT / 2, RED,
                              {'up': 'P2_UP', 'left': 'P2_LEFT', 'right': 'P2_RIGHT'}, 2)
        self.players = [self.player1, self.player2]
        self.winning_score = 5
        self.checkpoints = []
        self.active_checkpoint = None
        self.reset_game_elements()

    def reset_game_elements(self):
        self.player1.x = 150
        self.player1.y = SCREEN_HEIGHT / 2
        self.player1.velocity = [0.0, 0.0]
        self.player1.direction = 0
        self.player1.score = 0

        self.player2.x = SCREEN_WIDTH - 150
        self.player2.y = SCREEN_HEIGHT / 2
        self.player2.velocity = [0.0, 0.0]
        self.player2.direction = 0
        self.player2.score = 0
        
        self.generate_checkpoints()

    def generate_checkpoints(self):
        self.checkpoints = []
        num_checkpoints = 5
        checkpoint_radius = 25
        min_dist_from_edge = 100
        min_dist_between_checkpoints = 150

        for _ in range(num_checkpoints):
            while True:
                x = random.randint(min_dist_from_edge, SCREEN_WIDTH - min_dist_from_edge)
                y = random.randint(min_dist_from_edge, SCREEN_HEIGHT - min_dist_from_edge)
                new_checkpoint = Checkpoint(x, y, checkpoint_radius, GREEN)

                dist_p1 = pygame.math.Vector2(new_checkpoint.x - self.player1.x, new_checkpoint.y - self.player1.y).length()
                dist_p2 = pygame.math.Vector2(new_checkpoint.x - self.player2.x, new_checkpoint.y - self.player2.y).length()
                if dist_p1 < min_dist_between_checkpoints or dist_p2 < min_dist_between_checkpoints:
                    continue

                is_too_close = False
                for existing_cp in self.checkpoints:
                    dist_cp = pygame.math.Vector2(new_checkpoint.x - existing_cp.x, new_checkpoint.y - existing_cp.y).length()
                    if dist_cp < min_dist_between_checkpoints:
                        is_too_close = True
                        break
                if is_too_close:
                    continue
                
                self.checkpoints.append(new_checkpoint)
                break
        
        self.active_checkpoint = random.choice(self.checkpoints)
        self.active_checkpoint.is_active = True
        for cp in self.checkpoints:
            if cp != self.active_checkpoint:
                cp.is_active = False

    def draw_start_screen(self):
        SCREEN.fill(GRAY)
        
        title_text = FONT_LARGE.render("Pygame Racing Game!", True, BLACK)
        title_rect = title_text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT * 0.15))
        SCREEN.blit(title_text, title_rect)

        objective_text = FONT_MEDIUM.render(f"Objective: First player to reach {self.winning_score} checkpoints wins!", True, BLACK)
        objective_rect = objective_text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT * 0.35))
        SCREEN.blit(objective_text, objective_rect)

        p1_controls_title = FONT_MEDIUM.render("Player 1 Controls (Blue Car):", True, BLUE)
        p1_controls_title_rect = p1_controls_title.get_rect(center=(SCREEN_WIDTH / 4, SCREEN_HEIGHT * 0.5))
        SCREEN.blit(p1_controls_title, p1_controls_title_rect)

        p1_move_text = FONT_SMALL.render("UP: Accelerate", True, BLACK)
        p1_move_rect = p1_move_text.get_rect(center=(SCREEN_WIDTH / 4, SCREEN_HEIGHT * 0.5 + 40))
        SCREEN.blit(p1_move_text, p1_move_rect)
        
        p1_left_text = FONT_SMALL.render("LEFT: Turn Left", True, BLACK)
        p1_left_rect = p1_left_text.get_rect(center=(SCREEN_WIDTH / 4, SCREEN_HEIGHT * 0.5 + 70))
        SCREEN.blit(p1_left_text, p1_left_rect)
        
        p1_right_text = FONT_SMALL.render("RIGHT: Turn Right", True, BLACK)
        p1_right_rect = p1_right_text.get_rect(center=(SCREEN_WIDTH / 4, SCREEN_HEIGHT * 0.5 + 100))
        SCREEN.blit(p1_right_text, p1_right_rect)

        p2_controls_title = FONT_MEDIUM.render("Player 2 Controls (Red Car):", True, RED)
        p2_controls_title_rect = p2_controls_title.get_rect(center=(SCREEN_WIDTH * 3 / 4, SCREEN_HEIGHT * 0.5))
        SCREEN.blit(p2_controls_title, p2_controls_title_rect)

        p2_move_text = FONT_SMALL.render("UP: Accelerate", True, BLACK)
        p2_move_rect = p2_move_text.get_rect(center=(SCREEN_WIDTH * 3 / 4, SCREEN_HEIGHT * 0.5 + 40))
        SCREEN.blit(p2_move_text, p2_move_rect)
        
        p2_left_text = FONT_SMALL.render("LEFT: Turn Left", True, BLACK)
        p2_left_rect = p2_left_text.get_rect(center=(SCREEN_WIDTH * 3 / 4, SCREEN_HEIGHT * 0.5 + 70))
        SCREEN.blit(p2_left_text, p2_left_rect)
        
        p2_right_text = FONT_SMALL.render("RIGHT: Turn Right", True, BLACK)
        p2_right_rect = p2_right_text.get_rect(center=(SCREEN_WIDTH * 3 / 4, SCREEN_HEIGHT * 0.5 + 100))
        SCREEN.blit(p2_right_text, p2_right_rect)

        start_text = FONT_MEDIUM.render("Press SPACE to Start", True, BLACK)
        start_rect = start_text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT * 0.9))
        SCREEN.blit(start_text, start_rect)

        pygame.display.flip()

    def draw_game_screen(self, state):
        SCREEN.fill(LIGHT_GRAY)

        pygame.draw.rect(SCREEN, GRAY, (0, 0, SCREEN_WIDTH, 50))
        pygame.draw.rect(SCREEN, GRAY, (0, SCREEN_HEIGHT - 50, SCREEN_WIDTH, 50))
        pygame.draw.rect(SCREEN, GRAY, (0, 0, 50, SCREEN_HEIGHT))
        pygame.draw.rect(SCREEN, GRAY, (SCREEN_WIDTH - 50, 0, 50, SCREEN_HEIGHT))

        for player in self.players:
            player.update(state)
            player.draw(SCREEN)

        for cp in self.checkpoints:
            cp.draw(SCREEN)

        for player in self.players:
            if self.active_checkpoint and self.active_checkpoint.check_collision(player.get_rect()):
                player.score += 1
                self.active_checkpoint.is_active = False
                
                if player.score >= self.winning_score:
                    self.winner = player.player_id
                    self.game_state = "GAMEOVER"
                else:
                    available_checkpoints = [cp for cp in self.checkpoints if not cp.is_active and cp != self.active_checkpoint]
                    if available_checkpoints:
                        self.active_checkpoint = random.choice(available_checkpoints)
                        self.active_checkpoint.is_active = True
                    else: 
                        self.generate_checkpoints() 

        score_p1_text = FONT_SMALL.render(f"P1 Score: {self.player1.score}/{self.winning_score}", True, BLACK)
        SCREEN.blit(score_p1_text, (10, 10))
        score_p2_text = FONT_SMALL.render(f"P2 Score: {self.player2.score}/{self.winning_score}", True, BLACK)
        SCREEN.blit(score_p2_text, (SCREEN_WIDTH - score_p2_text.get_width() - 10, 10))

        pygame.display.flip()

    def draw_game_over_screen(self):
        SCREEN.fill(BLACK)
        
        winner_text = FONT_LARGE.render(f"Player {self.winner} Wins!", True, WHITE)
        winner_rect = winner_text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 50))
        SCREEN.blit(winner_text, winner_rect)

        restart_text = FONT_MEDIUM.render("Press R to Restart", True, WHITE)
        restart_rect = restart_text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 50))
        SCREEN.blit(restart_text, restart_rect)

        pygame.display.flip()

    def run(self):
        running = True
        clock = pygame.time.Clock()

        try:
            while running:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                    elif event.type == pygame.KEYDOWN:
                        if self.game_state == "START" and event.key == pygame.K_SPACE:
                            self.game_state = "PLAY"
                            self.reset_game_elements()
                        elif self.game_state == "GAMEOVER" and event.key == pygame.K_r:
                            self.game_state = "START"
                            self.reset_game_elements()

                state = self.input_handler.get_state()

                if self.game_state == "START":
                    self.draw_start_screen()
                elif self.game_state == "PLAY":
                    self.draw_game_screen(state)
                elif self.game_state == "GAMEOVER":
                    self.draw_game_over_screen()

                clock.tick(60)
        finally:
            self.input_handler.stop()
            pygame.quit()

if __name__ == "__main__":
    game = Game()
    game.run()