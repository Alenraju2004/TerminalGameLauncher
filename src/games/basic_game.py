import pygame
import sys
import math

try:
    # We continue to use GameInputHandler so that the Accessibility Modules 
    # (Head Tracker, Mouse Joystick, Blink Tracker) still inherently drive gameplay natively!
    from src.core.input_handler import GameInputHandler
except ImportError:
    print("Error: Could not import GameInputHandler.")
    sys.exit(1)

# Screen dimensions
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
BLUE = (0, 100, 255)
RED = (255, 50, 50)
GRAY = (100, 100, 100)

class Paddle:
    def __init__(self, x, y, color):
        self.rect = pygame.Rect(x, y, 15, 100)
        self.color = color
        self.speed = 7.0
        self.score = 0

    def move_up(self):
        self.rect.y -= int(self.speed)
        if self.rect.top < 0:
            self.rect.top = 0

    def move_down(self):
        self.rect.y += int(self.speed)
        if self.rect.bottom > SCREEN_HEIGHT:
            self.rect.bottom = SCREEN_HEIGHT

    def draw(self, screen):
        pygame.draw.rect(screen, self.color, self.rect)

    def reset_pos(self, y):
        self.rect.y = y

class Ball:
    def __init__(self):
        self.rect = pygame.Rect(SCREEN_WIDTH//2 - 10, SCREEN_HEIGHT//2 - 10, 20, 20)
        self.dx = 5.0
        self.dy = 5.0
        self.base_speed = 5.0

    def move(self):
        self.rect.x += int(self.dx)
        self.rect.y += int(self.dy)

        # Bounce top and bottom
        if self.rect.top <= 0:
            self.rect.top = 0
            self.dy *= -1
        elif self.rect.bottom >= SCREEN_HEIGHT:
            self.rect.bottom = SCREEN_HEIGHT
            self.dy *= -1

    def draw(self, screen):
        pygame.draw.rect(screen, WHITE, self.rect)

    def reset(self, direction):
        self.rect.center = (SCREEN_WIDTH//2, SCREEN_HEIGHT//2)
        # Randomize Y velocity slightly on serve
        self.dx = self.base_speed * direction
        self.dy = self.base_speed * (1 if direction > 0 else -1)

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Accessibility Pong")
        self.clock = pygame.time.Clock()
        
        self.font_title = pygame.font.SysFont('Arial', 72, bold=True)
        self.font_medium = pygame.font.SysFont('Arial', 36)
        self.font_small = pygame.font.SysFont('Arial', 24)
        
        # Using the Abstract Input Handler for universal controls
        self.input_handler = GameInputHandler()
        
        self.p1 = Paddle(30, SCREEN_HEIGHT//2 - 50, BLUE)
        self.p2 = Paddle(SCREEN_WIDTH - 45, SCREEN_HEIGHT//2 - 50, RED)
        self.ball = Ball()
        
        self.game_state = "START"
        self.winner = None
        self.max_score = 5

    def draw_text(self, text, font, color, x, y):
        surface = font.render(text, True, color)
        rect = surface.get_rect(center=(x, y))
        self.screen.blit(surface, rect)

    def draw_start_screen(self):
        self.screen.fill(BLACK)
        self.draw_text("ACCESSIBILITY PONG", self.font_title, WHITE, SCREEN_WIDTH//2, SCREEN_HEIGHT//4)
        
        self.draw_text("Controls:", self.font_medium, GRAY, SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 40)
        self.draw_text("Player 1 (Blue): W/S or Virtual Joystick/Head Tracker", self.font_small, BLUE, SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 10)
        self.draw_text("Player 2 (Red): Up/Down or Virtual Joystick/Head Tracker", self.font_small, RED, SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 50)
        
        self.draw_text(f"Objective: First to {self.max_score} points wins!", self.font_small, GRAY, SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 110)
        self.draw_text("Press SPACE to Start", self.font_medium, WHITE, SCREEN_WIDTH//2, SCREEN_HEIGHT*3//4)
        
        pygame.display.flip()

    def draw_game_over_screen(self):
        self.screen.fill(BLACK)
        self.draw_text("GAME OVER!", self.font_title, WHITE, SCREEN_WIDTH//2, SCREEN_HEIGHT//3)
        
        winner_text = "Player 1 Wins!" if self.winner == 1 else "Player 2 Wins!"
        winner_color = BLUE if self.winner == 1 else RED
        self.draw_text(winner_text, self.font_medium, winner_color, SCREEN_WIDTH//2, SCREEN_HEIGHT//2)
        
        self.draw_text("Press R to Restart", self.font_small, GRAY, SCREEN_WIDTH//2, SCREEN_HEIGHT*3//4)
        
        pygame.display.flip()

    def update_play(self):
        # Fetch abstract state tracking natively 
        state = self.input_handler.get_state()
        
        # Player 1 Movement
        if state.get("P1_UP"):
            self.p1.move_up()
        if state.get("P1_DOWN"):
            self.p1.move_down()
            
        # Player 2 Movement
        if state.get("P2_UP"):
            self.p2.move_up()
        if state.get("P2_DOWN"):
            self.p2.move_down()
            
        self.ball.move()
        
        # Collisions
        if self.ball.rect.colliderect(self.p1.rect):
            self.ball.rect.left = self.p1.rect.right
            self.ball.dx *= -1.1 # Speed up slightly dynamically
            
        if self.ball.rect.colliderect(self.p2.rect):
            self.ball.rect.right = self.p2.rect.left
            self.ball.dx *= -1.1

        # Scoring
        if self.ball.rect.left <= 0:
            self.p2.score += 1
            if self.p2.score >= self.max_score:
                self.winner = 2
                self.game_state = "GAMEOVER"
            else:
                self.ball.reset(1)
                
        elif self.ball.rect.right >= SCREEN_WIDTH:
            self.p1.score += 1
            if self.p1.score >= self.max_score:
                self.winner = 1
                self.game_state = "GAMEOVER"
            else:
                self.ball.reset(-1)

    def draw_play(self):
        self.screen.fill(BLACK)
        
        # Draw Center Line
        pygame.draw.line(self.screen, GRAY, (SCREEN_WIDTH//2, 0), (SCREEN_WIDTH//2, SCREEN_HEIGHT), 2)
        
        self.p1.draw(self.screen)
        self.p2.draw(self.screen)
        self.ball.draw(self.screen)
        
        self.draw_text(str(self.p1.score), self.font_title, BLUE, SCREEN_WIDTH//4, 50)
        self.draw_text(str(self.p2.score), self.font_title, RED, SCREEN_WIDTH*3//4, 50)
        
        pygame.display.flip()

    def run(self):
        running = True
        try:
            while running:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                        sys.exit()
                        
                    if event.type == pygame.KEYDOWN:
                        if self.game_state == "START" and event.key == pygame.K_SPACE:
                            self.p1.score = 0
                            self.p2.score = 0
                            self.ball.reset(1)
                            self.game_state = "PLAY"
                        elif self.game_state == "GAMEOVER" and event.key == pygame.K_r:
                            self.p1.score = 0
                            self.p2.score = 0
                            self.ball.reset(1)
                            self.p1.reset_pos(SCREEN_HEIGHT//2 - 50)
                            self.p2.reset_pos(SCREEN_HEIGHT//2 - 50)
                            self.game_state = "START"
                            
                if self.game_state == "START":
                    self.draw_start_screen()
                elif self.game_state == "PLAY":
                    self.update_play()
                    self.draw_play()
                elif self.game_state == "GAMEOVER":
                    self.draw_game_over_screen()
                    
                self.clock.tick(FPS)
        finally:
            self.input_handler.stop()
            pygame.quit()

if __name__ == "__main__":
    game = Game()
    game.run()
