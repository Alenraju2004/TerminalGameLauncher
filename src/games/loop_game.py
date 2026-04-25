# Neon Race Rumble
import pygame
import sys
import random
import math

try:
    from src.core.input_handler import GameInputHandler
except ImportError:
    print("Error: Could not import GameInputHandler.")
    sys.exit(1)

# 2. Constants
# Flexible Resolution Setup
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60

# Neon/Cyberpunk/High-Contrast Arcade Color Palette
COLOR_BG = (20, 0, 40)             # Deep Dark Purple background
COLOR_P1 = (0, 255, 255)           # Cyan for Player 1
COLOR_P2 = (255, 0, 255)           # Magenta for Player 2
COLOR_TRACK = (0, 255, 0)          # Electric Green for track elements
COLOR_WALL = (100, 255, 100)       # Lighter Electric Green for track boundary walls
COLOR_TEXT_PRIMARY = (255, 255, 255) # Bright White for primary text
COLOR_TEXT_SHADOW = (50, 50, 50)    # Dark Gray for text drop shadows
COLOR_PARTICLE_GLOW = (255, 255, 0) # Yellowish glow for lap/dash particles
COLOR_PARTICLE_ORANGE = (255, 165, 0) # Orange for collision particles

# Game Physics & Player Properties
PLAYER_RADIUS = 15
PLAYER_MAX_SPEED = 250.0 # pixels per second
PLAYER_ACCEL = 1000.0    # pixels per second^2
PLAYER_DECEL_FACTOR = 0.95 # Factor applied to velocity when no input
PLAYER_FRICTION_FACTOR = 0.9  # Constant friction applied always
MAX_LAPS = 3 # Win condition

# Screen Shake Properties
SHAKE_DURATION_DEFAULT = 20 # frames for general shakes
SHAKE_INTENSITY_DEFAULT = 5 # pixels offset

# Track & Checkpoint Properties
TRACK_INNER_WIDTH = 400
TRACK_INNER_HEIGHT = 200
TRACK_LINE_THICKNESS = 5
CHECKPOINT_SIZE = 40

# Particle System Properties
PARTICLE_LIFETIME = 30 # frames
PARTICLE_MAX_SIZE = 10
PARTICLE_SPEED_MAG = 150.0 # pixels per second

# 3. Player Class
class Player:
    def __init__(self, x, y, color, controls_prefix):
        self.x = float(x)
        self.y = float(y)
        self.vx = 0.0
        self.vy = 0.0
        self.color = color
        self.controls_prefix = controls_prefix
        self.radius = PLAYER_RADIUS
        self.laps = 0
        self.current_checkpoint_index = 0 # Index of the next checkpoint to hit
        self.score_particles_timer = 0 # Timer for continuous particles on scoring

    def update(self, input_state, dt):
        # Apply constant friction
        self.vx *= (PLAYER_FRICTION_FACTOR ** dt) 
        self.vy *= (PLAYER_FRICTION_FACTOR ** dt)

        # Apply deceleration if no movement input
        if not (input_state.get(f"{self.controls_prefix}_UP") or
                input_state.get(f"{self.controls_prefix}_DOWN") or
                input_state.get(f"{self.controls_prefix}_LEFT") or
                input_state.get(f"{self.controls_prefix}_RIGHT")):
            self.vx *= (PLAYER_DECEL_FACTOR ** dt)
            self.vy *= (PLAYER_DECEL_FACTOR ** dt)

        # Apply acceleration based on input
        accel_x = 0.0
        accel_y = 0.0
        if input_state.get(f"{self.controls_prefix}_UP"):
            accel_y -= PLAYER_ACCEL
        if input_state.get(f"{self.controls_prefix}_DOWN"):
            accel_y += PLAYER_ACCEL
        if input_state.get(f"{self.controls_prefix}_LEFT"):
            accel_x -= PLAYER_ACCEL
        if input_state.get(f"{self.controls_prefix}_RIGHT"):
            accel_x += PLAYER_ACCEL
        
        # Normalize diagonal acceleration to prevent faster diagonal movement
        if accel_x != 0 and accel_y != 0:
            norm = math.sqrt(accel_x**2 + accel_y**2)
            accel_x = (accel_x / norm) * PLAYER_ACCEL
            accel_y = (accel_y / norm) * PLAYER_ACCEL

        self.vx += accel_x * dt
        self.vy += accel_y * dt

        # Cap speed
        current_speed = math.sqrt(self.vx**2 + self.vy**2)
        if current_speed > PLAYER_MAX_SPEED:
            scale = PLAYER_MAX_SPEED / current_speed
            self.vx *= scale
            self.vy *= scale

        # Update position
        self.x += self.vx * dt
        self.y += self.vy * dt

        # Keep player within screen bounds, bounce
        if self.x - self.radius < 0:
            self.x = self.radius
            self.vx *= -0.8 # Bounce with some energy loss
        elif self.x + self.radius > SCREEN_WIDTH:
            self.x = SCREEN_WIDTH - self.radius
            self.vx *= -0.8
        
        if self.y - self.radius < 0:
            self.y = self.radius
            self.vy *= -0.8
        elif self.y + self.radius > SCREEN_HEIGHT:
            self.y = SCREEN_HEIGHT - self.radius
            self.vy *= -0.8

    def get_rect(self):
        # Returns an integer-based rect for collision detection
        return pygame.Rect(int(self.x - self.radius), int(self.y - self.radius),
                           self.radius * 2, self.radius * 2)

    def draw(self, surface, offset=(0, 0)):
        # Player body
        pygame.draw.circle(surface, self.color, (int(self.x + offset[0]), int(self.y + offset[1])), self.radius)
        # Direction indicator
        if math.sqrt(self.vx**2 + self.vy**2) > 50: # Only draw if moving significantly
            dir_norm_x = self.vx / (math.sqrt(self.vx**2 + self.vy**2))
            dir_norm_y = self.vy / (math.sqrt(self.vx**2 + self.vy**2))
            pygame.draw.line(surface, COLOR_TEXT_PRIMARY, 
                             (int(self.x + offset[0]), int(self.y + offset[1])),
                             (int(self.x + dir_norm_x * self.radius * 0.7 + offset[0]), 
                              int(self.y + dir_norm_y * self.radius * 0.7 + offset[1])), 2)

# Particle class for visual effects (collisions, scores, etc.)
class Particle:
    def __init__(self, x, y, color, speed_mult=1.0):
        self.x = float(x)
        self.y = float(y)
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(PARTICLE_SPEED_MAG * 0.5, PARTICLE_SPEED_MAG * 1.5) * speed_mult
        self.vx = speed * math.cos(angle)
        self.vy = speed * math.sin(angle)
        self.base_color = color # Store base color without alpha
        self.size = random.randint(3, PARTICLE_MAX_SIZE)
        self.lifetime = PARTICLE_LIFETIME
        self.max_lifetime = PARTICLE_LIFETIME
        self.growth_rate = random.uniform(0.1, 0.5) # Pixels per frame at 60 FPS

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.size += self.growth_rate * dt * FPS # Scale growth by dt for frame-rate independence
        self.lifetime -= 1
        
        # Fade out particle
        alpha = int(255 * (self.lifetime / self.max_lifetime))
        if alpha < 0: alpha = 0 # Clamp alpha to 0
        self.color = self.base_color[:3] + (alpha,) # Create new color tuple with alpha

    def draw(self, surface, offset=(0, 0)):
        if self.lifetime > 0:
            # Draw on a temporary surface with SRCALPHA for transparency
            # Create a small surface just large enough for the particle
            draw_size = int(self.size * 2)
            if draw_size <= 0: return # Don't draw if size is too small

            particle_surface = pygame.Surface((draw_size, draw_size), pygame.SRCALPHA)
            particle_surface.fill((0,0,0,0)) # Transparent background
            
            # Draw the particle (circle or rectangle)
            if random.random() < 0.5: # Mix of circles and rectangles
                 pygame.draw.circle(particle_surface, self.color, (draw_size // 2, draw_size // 2), draw_size // 2)
            else:
                 pygame.draw.rect(particle_surface, self.color, (0, 0, draw_size, draw_size))

            surface.blit(particle_surface, (int(self.x - self.size + offset[0]), int(self.y - self.size + offset[1])))


# 4. Game Class (Manages game state, logic, and drawing)
class Game:
    def __init__(self, screen):
        self.screen = screen
        self.game_state = "START" # Initial state: START, PLAY, GAMEOVER
        
        # Setup fonts for UI
        self.font_title = pygame.font.SysFont("Impact", 80, bold=True)
        self.font_header = pygame.font.SysFont("Impact", 48)
        self.font_body = pygame.font.SysFont("Arial", 28)
        self.font_small = pygame.font.SysFont("Arial", 20)

        self.players = []
        self.particles = []
        self.winner = None

        # Screen shake state
        self.shake_duration = 0
        self.shake_offset = (0, 0)
        self.shake_intensity = SHAKE_INTENSITY_DEFAULT

        # Define the central track obstacle (a rectangle)
        self.track_rect = pygame.Rect(SCREEN_WIDTH / 2 - TRACK_INNER_WIDTH / 2,
                                      SCREEN_HEIGHT / 2 - TRACK_INNER_HEIGHT / 2,
                                      TRACK_INNER_WIDTH, TRACK_INNER_HEIGHT)
        
        # Define checkpoints for lap detection. Players must hit these in sequence.
        # Clockwise path around the central obstacle: Top-Right, Bottom-Right, Bottom-Left, Top-Left
        self.checkpoints = [
            # Checkpoint 1: Top-right corner (offset slightly outside track)
            pygame.Rect(self.track_rect.right - CHECKPOINT_SIZE // 2, self.track_rect.top - CHECKPOINT_SIZE // 2, 
                        CHECKPOINT_SIZE, CHECKPOINT_SIZE),
            # Checkpoint 2: Bottom-right corner
            pygame.Rect(self.track_rect.right - CHECKPOINT_SIZE // 2, self.track_rect.bottom - CHECKPOINT_SIZE // 2, 
                        CHECKPOINT_SIZE, CHECKPOINT_SIZE),
            # Checkpoint 3: Bottom-left corner
            pygame.Rect(self.track_rect.left - CHECKPOINT_SIZE // 2, self.track_rect.bottom - CHECKPOINT_SIZE // 2, 
                        CHECKPOINT_SIZE, CHECKPOINT_SIZE),
            # Checkpoint 4: Top-left corner
            pygame.Rect(self.track_rect.left - CHECKPOINT_SIZE // 2, self.track_rect.top - CHECKPOINT_SIZE // 2, 
                        CHECKPOINT_SIZE, CHECKPOINT_SIZE),
        ]

        self._reset_game() # Initialize game state

    def _reset_game(self):
        # Reset player positions, velocities, laps, and current checkpoints
        self.players = [
            Player(SCREEN_WIDTH / 2 - 150, SCREEN_HEIGHT / 2, COLOR_P1, "P1"),
            Player(SCREEN_WIDTH / 2 + 150, SCREEN_HEIGHT / 2, COLOR_P2, "P2")
        ]
        self.particles = []
        self.winner = None
        self.shake_duration = 0
        self.shake_offset = (0, 0)
        
        for p in self.players:
            p.laps = 0
            p.current_checkpoint_index = 0
            p.vx, p.vy = 0.0, 0.0 # Stop players

    def _draw_text(self, surface, text, font, color, x, y, shadow_color=None, shadow_offset=(3, 3), center=False):
        # Helper function to draw text with an optional drop shadow
        if shadow_color:
            shadow_text_surface = font.render(text, True, shadow_color)
            if center:
                text_rect = shadow_text_surface.get_rect(center=(x + shadow_offset[0], y + shadow_offset[1]))
            else:
                text_rect = shadow_text_surface.get_rect(x=x + shadow_offset[0], y=y + shadow_offset[1])
            surface.blit(shadow_text_surface, text_rect)

        main_text_surface = font.render(text, True, color)
        if center:
            text_rect = main_text_surface.get_rect(center=(x, y))
        else:
            text_rect = main_text_surface.get_rect(x=x, y=y)
        surface.blit(main_text_surface, text_rect)

    def _start_shake(self, duration=SHAKE_DURATION_DEFAULT, intensity=SHAKE_INTENSITY_DEFAULT):
        self.shake_duration = duration
        self.shake_intensity = intensity

    def _update_shake(self):
        if self.shake_duration > 0:
            self.shake_offset = (random.randint(-self.shake_intensity, self.shake_intensity),
                                 random.randint(-self.shake_intensity, self.shake_intensity))
            self.shake_duration -= 1
        else:
            self.shake_offset = (0, 0)

    def _update_game(self, input_state, dt):
        self._update_shake() # Update screen shake regardless of game events

        # Update players and handle collisions
        for player in self.players:
            player.update(input_state, dt)

            # Player-Track Obstacle collision
            player_rect = player.get_rect()
            if player_rect.colliderect(self.track_rect):
                self._start_shake(duration=5, intensity=2) # Minor shake for track collision

                # Simple push-back from the track obstacle
                dx = player.x - self.track_rect.centerx
                dy = player.y - self.track_rect.centery
                # Find penetration depth
                if abs(dx) / (self.track_rect.width / 2 + player.radius) > abs(dy) / (self.track_rect.height / 2 + player.radius):
                    # Collision is horizontal
                    if dx > 0: # Player is to the right
                        player.x = self.track_rect.right + player.radius
                    else: # Player is to the left
                        player.x = self.track_rect.left - player.radius
                    player.vx *= -0.7 # Bounce with energy loss
                else:
                    # Collision is vertical
                    if dy > 0: # Player is below
                        player.y = self.track_rect.bottom + player.radius
                    else: # Player is above
                        player.y = self.track_rect.top - player.radius
                    player.vy *= -0.7 # Bounce with energy loss
                
                # Generate collision particles
                for _ in range(5):
                    self.particles.append(Particle(player.x, player.y, player.color))

            # Checkpoint progression logic
            next_checkpoint_rect = self.checkpoints[player.current_checkpoint_index]
            if player.get_rect().colliderect(next_checkpoint_rect):
                player.current_checkpoint_index = (player.current_checkpoint_index + 1) % len(self.checkpoints)
                # If player wrapped around to checkpoint 0, a full lap is completed
                if player.current_checkpoint_index == 0:
                    player.laps += 1
                    self._start_shake(duration=10, intensity=3) # Small shake for lap completion
                    # Generate burst of particles for lap completion
                    for _ in range(15):
                        self.particles.append(Particle(player.x, player.y, COLOR_PARTICLE_GLOW, speed_mult=1.5))

        # Player-player collision detection and resolution
        p1, p2 = self.players[0], self.players[1]
        distance_sq = (p1.x - p2.x)**2 + (p1.y - p2.y)**2
        min_distance = p1.radius + p2.radius
        
        if distance_sq < min_distance**2:
            self._start_shake(duration=SHAKE_DURATION_DEFAULT, intensity=SHAKE_INTENSITY_DEFAULT) # Major shake

            distance = math.sqrt(distance_sq)
            overlap = min_distance - distance

            # Avoid division by zero if players are perfectly overlapped
            if distance == 0:
                nx, ny = random.uniform(-1, 1), random.uniform(-1, 1)
                norm = math.sqrt(nx**2 + ny**2)
                if norm == 0: norm = 1 # Fallback
                nx /= norm
                ny /= norm
            else:
                nx = (p1.x - p2.x) / distance # Normal vector x
                ny = (p1.y - p2.y) / distance # Normal vector y

            # Separate players to resolve overlap
            p1.x += nx * overlap / 2
            p1.y += ny * overlap / 2
            p2.x -= nx * overlap / 2
            p2.y -= ny * overlap / 2

            # Simplified elastic collision response (velocity exchange along normal)
            # Relative velocity components along the normal vector
            v1n = p1.vx * nx + p1.vy * ny
            v2n = p2.vx * nx + p2.vy * ny

            # Exchange normal velocities (with some energy loss)
            new_v1n = v2n * 0.8
            new_v2n = v1n * 0.8

            # Calculate tangential velocity components (perpendicular to normal)
            v1t = p1.vx * (-ny) + p1.vy * nx
            v2t = p2.vx * (-ny) + p2.vy * nx
            
            # Update velocities
            p1.vx = new_v1n * nx + v1t * (-ny)
            p1.vy = new_v1n * ny + v1t * nx
            p2.vx = new_v2n * nx + v2t * (-ny)
            p2.vy = new_v2n * ny + v2t * nx

            # Generate collision particles at the point of impact
            mid_x = (p1.x + p2.x) / 2
            mid_y = (p1.y + p2.y) / 2
            for _ in range(15):
                self.particles.append(Particle(mid_x, mid_y, random.choice([p1.color, p2.color, COLOR_PARTICLE_ORANGE])))

        # Update and clean up particles
        self.particles = [p for p in self.particles if p.lifetime > 0]
        for particle in self.particles:
            particle.update(dt)

        # Check for win condition
        for player in self.players:
            if player.laps >= MAX_LAPS:
                self.winner = player
                self.game_state = "GAMEOVER"
                # Major screen shake for game end
                self._start_shake(duration=SHAKE_DURATION_DEFAULT * 2, intensity=SHAKE_INTENSITY_DEFAULT * 1.5) 
                return

    def _draw_game(self, surface):
        surface.fill(COLOR_BG)

        # Apply screen shake offset to all drawing
        ox, oy = self.shake_offset

        # Draw track boundaries (central rectangle)
        pygame.draw.rect(surface, COLOR_WALL, 
                         pygame.Rect(self.track_rect.x + ox, self.track_rect.y + oy, 
                                     self.track_rect.width, self.track_rect.height), TRACK_LINE_THICKNESS)
        
        # Draw the next checkpoint for each player
        for player in self.players:
            current_cp_rect = self.checkpoints[player.current_checkpoint_index]
            
            # Transparent fill for checkpoint area
            cp_surface = pygame.Surface((current_cp_rect.width, current_cp_rect.height), pygame.SRCALPHA)
            cp_surface.fill(player.color[:3] + (100,)) # Player color with some transparency
            surface.blit(cp_surface, (current_cp_rect.x + ox, current_cp_rect.y + oy))

            # Outline for checkpoint
            pygame.draw.rect(surface, player.color, 
                             pygame.Rect(current_cp_rect.x + ox, current_cp_rect.y + oy, 
                                         current_cp_rect.width, current_cp_rect.height), 2)

        # Draw particles (before players for layer effect)
        for particle in self.particles:
            particle.draw(surface, (ox, oy))

        # Draw players
        for player in self.players:
            player.draw(surface, (ox, oy))

        # Draw UI (Lap counters)
        p1_text = f"P1 Laps: {self.players[0].laps}/{MAX_LAPS}"
        p2_text = f"P2 Laps: {self.players[1].laps}/{MAX_LAPS}"
        self._draw_text(surface, p1_text, self.font_body, COLOR_P1, 20, 20, COLOR_TEXT_SHADOW)
        self._draw_text(surface, p2_text, self.font_body, COLOR_P2, SCREEN_WIDTH - 20 - self.font_body.size(p2_text)[0], 20, COLOR_TEXT_SHADOW)


    def _update_start_screen(self, input_state):
        # Transition to PLAY state if P1_UP or P2_UP is pressed
        if input_state.get("P1_UP") or input_state.get("P2_UP"):
            self.game_state = "PLAY"
            self._reset_game() # Ensure a fresh game starts

    def _draw_start_screen(self, surface):
        surface.fill(COLOR_BG)
        center_x, center_y = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2

        self._draw_text(surface, "NEON RACE RUMBLE", self.font_title, COLOR_TEXT_PRIMARY, center_x, center_y - 200, COLOR_TEXT_SHADOW, center=True)
        
        self._draw_text(surface, "Controls:", self.font_header, COLOR_TRACK, center_x, center_y - 80, COLOR_TEXT_SHADOW, center=True)
        self._draw_text(surface, "Player 1: D-Pad (UP, DOWN, LEFT, RIGHT keys)", self.font_body, COLOR_P1, center_x, center_y - 30, COLOR_TEXT_SHADOW, center=True)
        self._draw_text(surface, "Player 2: D-Pad (W, S, A, D keys)", self.font_body, COLOR_P2, center_x, center_y + 10, COLOR_TEXT_SHADOW, center=True)
        
        self._draw_text(surface, "Objective:", self.font_header, COLOR_TRACK, center_x, center_y + 100, COLOR_TEXT_SHADOW, center=True)
        self._draw_text(surface, f"Be the first to complete {MAX_LAPS} laps around the central track!", self.font_body, COLOR_TEXT_PRIMARY, center_x, center_y + 150, COLOR_TEXT_SHADOW, center=True)
        
        self._draw_text(surface, "Press UP to Start", self.font_header, COLOR_TEXT_PRIMARY, center_x, SCREEN_HEIGHT - 100, COLOR_TEXT_SHADOW, center=True)

    def _update_game_over_screen(self, input_state):
        self._update_shake() # Continue screen shake effect on game over screen
        # Transition back to START state if P1_UP or P2_UP is pressed
        if input_state.get("P1_UP") or input_state.get("P2_UP"):
            self.game_state = "START" 
            self._reset_game() # Reset game state for a new round

    def _draw_game_over_screen(self, surface):
        surface.fill(COLOR_BG)
        # Apply screen shake offset to all drawing
        ox, oy = self.shake_offset

        center_x, center_y = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
        
        winner_color = COLOR_TEXT_PRIMARY
        winner_name = "NO ONE"
        if self.winner:
            winner_name = f"PLAYER {1 if self.winner == self.players[0] else 2}"
            winner_color = self.winner.color

        self._draw_text(surface, "GAME OVER!", self.font_title, COLOR_TRACK, center_x + ox, center_y - 100 + oy, COLOR_TEXT_SHADOW, center=True)
        self._draw_text(surface, f"{winner_name} WINS!", self.font_header, winner_color, center_x + ox, center_y + oy, COLOR_TEXT_SHADOW, center=True)
        self._draw_text(surface, "Press UP to Restart", self.font_body, COLOR_TEXT_PRIMARY, center_x + ox, SCREEN_HEIGHT - 100 + oy, COLOR_TEXT_SHADOW, center=True)

        # Draw particles that might still be active from the game end event
        for particle in self.particles:
            particle.draw(surface, (ox, oy))


    # Main update logic, dispatches based on game_state
    def update(self, input_state, dt):
        if self.game_state == "START":
            self._update_start_screen(input_state)
        elif self.game_state == "PLAY":
            self._update_game(input_state, dt)
        elif self.game_state == "GAMEOVER":
            self._update_game_over_screen(input_state)

    # Main drawing logic, dispatches based on game_state
    def draw(self, surface):
        if self.game_state == "START":
            self._draw_start_screen(surface)
        elif self.game_state == "PLAY":
            self._draw_game(surface)
        elif self.game_state == "GAMEOVER":
            self._draw_game_over_screen(surface)


# Main Function (Orchestrates Pygame initialization and the main loop)
def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Neon Race Rumble")
    clock = pygame.time.Clock()

    # CRITICAL: Instantiate GameInputHandler
    input_handler = GameInputHandler() 

    # Create the main game instance
    game = Game(screen)

    running = True
    while running:
        # Standard Pygame event loop for window closing
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # CRITICAL: Get current input state from GameInputHandler.
        # DO NOT pass Pygame events to GameInputHandler.
        input_state = input_handler.get_state() 

        # Calculate delta time for frame-rate independent movement
        dt = clock.tick(FPS) / 1000.0 # Convert milliseconds to seconds

        # Update game logic
        game.update(input_state, dt)
        
        # Draw all game elements for the current state
        game.draw(screen)

        # Update the full display surface
        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()