import pygame, sys, random, math
from typing import List
pygame.init()

# ---------- window ----------
WIDTH, HEIGHT = 1280, 720
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("67 Water RPG – Quest for the Princess")
CLOCK = pygame.time.Clock()
FPS = 120

# Debug mode - press D to toggle
DEBUG_MODE = False

# game state
class GameState:
    def __init__(self):
        self.camera_x = 0.0
        self.screen_shake = 0
        self.screen_shake_intensity = 0
        self.debug_mode = False

game_state = GameState()

# character scale (bigger characters)
CHAR_SCALE = 1.6

# ---------- colors ----------
SKY = (90,140,255)
GROUND = (40,100,40)
WHITE = (255,255,255)
BLACK = (20,20,20)
RED = (220,60,60)
GREEN = (60,200,80)
BLUE = (60,140,255)
GRAY = (100,100,100)
YELLOW = (250,230,120)
CYAN = (100,200,255)

FONT = pygame.font.Font(None,28)
BIG = pygame.font.Font(None,60)

# ---------- helpers ----------
def draw_text_center(text,y,size=32,color=WHITE):
    f = pygame.font.Font(None,size)
    surf = f.render(text,True,color)
    SCREEN.blit(surf,(WIDTH//2 - surf.get_width()//2,y))

def apply_screen_shake():
    """Apply slight random offset for screen shake effect."""
    if game_state.screen_shake > 0:
        offset_x = random.randint(-game_state.screen_shake_intensity, game_state.screen_shake_intensity)
        offset_y = random.randint(-game_state.screen_shake_intensity, game_state.screen_shake_intensity)
        game_state.screen_shake -= 1
        return offset_x, offset_y
    return 0, 0

class Particle(pygame.sprite.Sprite):
    """Simple particle effect with gravity and fade."""
    def __init__(self, x, y, vx, vy, color, lifetime=20):
        super().__init__()
        self.x = float(x)
        self.y = float(y)
        self.vx = vx
        self.vy = vy
        self.lifetime = lifetime
        self.max_lifetime = lifetime
        self.color = color
        self.image = pygame.Surface((4, 4), pygame.SRCALPHA)
        pygame.draw.circle(self.image, color, (2, 2), 2)
        self.rect = self.image.get_rect(center=(x, y))

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.15  # gravity
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.kill()
            return
        # fade out
        alpha = int(255 * (self.lifetime / self.max_lifetime))
        self.image.fill((0, 0, 0, 0))
        pygame.draw.circle(self.image, self.color + (alpha,), (2, 2), 2)
        self.rect.center = (int(self.x), int(self.y))

    def draw(self, s):
        """Draw particle to screen."""
        s.blit(self.image, self.rect)

# ---------- basic sprites ----------
class Platform(pygame.sprite.Sprite):
    def __init__(self,x,y,w,h):
        super().__init__()
        self.image = pygame.Surface((w,h))
        self.image.fill(GROUND)
        self.rect = self.image.get_rect(topleft=(x,y))

class SwordSwing(pygame.sprite.Sprite):
    def __init__(self, owner):
        super().__init__()
        # swing duration and active frames (slower, overhead swing)
        self.timer = 22
        self.active_start = 7
        self.active_end = 16

        self.facing = getattr(owner, "facing", 1)
        self.owner = owner
        self.did_hit = set()

        # New rigid sword style: handle/pivot is at the surface center
        blade_length = int(70 * CHAR_SCALE)
        blade_w = max(2, int(4 * CHAR_SCALE))
        handle_len = int(12 * CHAR_SCALE)
        size_w = blade_length + handle_len + int(40 * CHAR_SCALE)
        size_h = int(24 * CHAR_SCALE)

        self.base_right = pygame.Surface((size_w, size_h), pygame.SRCALPHA)
        cx = size_w // 2
        cy = size_h // 2
        # handle centered at pivot
        pygame.draw.rect(self.base_right, (60,30,10), (cx - handle_len//2, cy - int(handle_len*0.2), handle_len, int(handle_len*0.4)))
        pygame.draw.circle(self.base_right, (180,140,60), (cx - handle_len//2 - int(4*CHAR_SCALE), cy), int(3*CHAR_SCALE))
        # blade extends to the right from pivot
        blade_rect = pygame.Rect(cx, cy - blade_w//2, blade_length, blade_w)
        pygame.draw.rect(self.base_right, (220,220,230), blade_rect)
        tip = [(cx + blade_length, cy - blade_w//2), (cx + blade_length + int(10*CHAR_SCALE), cy), (cx + blade_length, cy + blade_w//2)]
        pygame.draw.polygon(self.base_right, (220,220,230), tip)
        pygame.draw.line(self.base_right, WHITE, (cx, cy - blade_w//2 + 1), (cx + blade_length, cy - blade_w//2 + 1), max(1, int(1*CHAR_SCALE)))

        # mirrored for left
        self.base_left = pygame.transform.flip(self.base_right, True, False)

        # image will be replaced with rotated surface each frame
        self.image = self.base_right.copy()
        self.rect = self.image.get_rect()

    def update(self):
        self.timer -= 1
        if self.timer <= 0:
            self.kill()
            return

        life = 22
        prog = max(0.0, min(1.0, (life - self.timer) / life))
        # Smooth easing: cubic ease-in-out for natural deceleration/acceleration feel
        if prog < 0.5:
            ease = 2 * prog * prog
        else:
            ease = -1 + (4 - 2 * prog) * prog

        # angle sweep for top-down overhead swing (downward arc)
        if self.facing == 1:
            start_ang, end_ang = -160, 10  # swing from top-left to bottom-right
        else:
            start_ang, end_ang = 160, -10  # swing from top-right to bottom-left
        angle = start_ang + (end_ang - start_ang) * ease

        base = self.base_right if self.facing == 1 else self.base_left
        rot = pygame.transform.rotate(base, angle)

        # draw translucent trails of the rotated blade for motion blur
        img = pygame.Surface(rot.get_size(), pygame.SRCALPHA)
        for i in range(3):
            t = (i + 1) / 4.0
            alpha = int(120 * (1 - t) * (1 - ease))
            trail = rot.copy()
            trail.fill((255,255,255,alpha), special_flags=pygame.BLEND_RGBA_MULT)
            offset_x = int(-t * 6 * self.facing)
            img.blit(trail, (offset_x + 2 * i, 0))
        # main blade on top
        img.blit(rot, (0,0))

        # position pivot (image center) floating out in front of player, not at body
        hand_x = self.owner.rect.centerx + self.facing * (self.owner.rect.width // 2 + int(20 * CHAR_SCALE))
        hand_y = self.owner.rect.centery  # center height
        self.image = img
        self.rect = self.image.get_rect(center=(hand_x, hand_y))

    def damage_active(self):
        life = 22
        elapsed = life - self.timer
        return self.active_start <= elapsed <= self.active_end


class MagicBolt(pygame.sprite.Sprite):
    """Simple projectile used by Mage class."""
    def __init__(self, owner):
        super().__init__()
        self.owner = owner
        # Nerfed projectile speed for balance (was 18)
        self.speed = 14 * owner.facing
        self.image = pygame.Surface((int(12*CHAR_SCALE), int(8*CHAR_SCALE)), pygame.SRCALPHA)
        pygame.draw.ellipse(self.image, (150,180,255), (0,0,self.image.get_width(), self.image.get_height()))
        self.rect = self.image.get_rect(center=(owner.rect.centerx + owner.facing* (owner.rect.width//2 + 10), owner.rect.centery))
        # Shorter lifetime so mages can't spam long-range shots across whole map
        self.life = 30
        self.is_projectile = True
        self.did_hit = set()

    def update(self):
        self.rect.x += int(self.speed)
        self.life -= 1
        if self.life <= 0:
            self.kill()

# ---------- entities ----------
class Player(pygame.sprite.Sprite):
    def __init__(self, x, y, class_name='Werrior'):
        super().__init__()
        # scale sizes
        self.scale = CHAR_SCALE
        w = int(32 * self.scale)
        h = int(48 * self.scale)
        self.image = pygame.Surface((w, h), pygame.SRCALPHA)
        self.rect = self.image.get_rect(topleft=(x, y))
        self.vel_y = 0
        # default stats (may be overridden by class)
        self.speed = 6
        self.jump = int(13 * (1 if self.scale <= 1 else 1.0))
        self.class_name = class_name
        self.max_health = 120
        self.health = self.max_health
        self.water = 50
        # inventory: simple list of item names
        self.inventory: List[str] = []
        self.facing = 1
        self.att_cd = 0
        # dash state: cooldown, active timer, velocity, invulnerability frames
        self.dash_cd = 0
        self.dash_timer = 0
        self.dash_vel = 0
        self.invuln = 0
        # walking animation phase
        self.walk_phase = 0
        # jump tracking (single jump only)
        self.jumps = 0
        self.max_jumps = 1
        # track whether jump key was held last frame to enforce single jump per press
        self.jump_held_last = False
        # cast timer for Mage casting animation (frames)
        self.cast_timer = 0
        self.vel_x = 0.0  # smooth horizontal velocity
        self.on_ground_last = False
        self.land_time = 0
        # potion effect timers
        self.strength_timer = 0
        self.knockback_timer = 0
        self.knockback_boost = 1.0
        if self.class_name.lower().startswith('war'):
            self.max_health = 160
            self.health = self.max_health
            self.speed = 5
            self.attack_bonus = 6
            self.base_attack_bonus = 6
            self.dash_strength = 26
            self.dash_invuln = 14
        elif self.class_name.lower().startswith('ran'):
            self.max_health = 110
            self.health = self.max_health
            self.speed = 8
            self.attack_bonus = 2
            self.base_attack_bonus = 2
            self.dash_strength = 20
            self.dash_invuln = 10
        elif self.class_name.lower().startswith('mag'):
            self.max_health = 90
            self.health = self.max_health
            self.speed = 5
            self.attack_bonus = 10
            self.base_attack_bonus = 10
            self.dash_strength = 18
            self.dash_invuln = 10
        else:
            self.attack_bonus = 0
            self.base_attack_bonus = 0
            self.dash_strength = 22
            self.dash_invuln = 12

    def add_item(self, item: str):
        self.inventory.append(item)

    def has_item(self, item: str) -> bool:
        return item in self.inventory

    def use_potion(self, potion_type: str = "Health") -> bool:
        """Consume a Potion. Returns True if used."""
        for i, it in enumerate(self.inventory):
            if it.lower() == potion_type.lower():
                if potion_type.lower() == 'health':
                    self.health = min(self.max_health, self.health + 60)
                elif potion_type.lower() == 'strength':
                    self.attack_bonus = self.base_attack_bonus + 25
                    self.strength_timer = 120  # ~1 second at 120 FPS
                elif potion_type.lower() == 'knockback':
                    self.knockback_boost = 1.8
                    self.knockback_timer = 120
                del self.inventory[i]
                return True
        return False

    def update(self, keys, plats, swings, particles):
        # update potion effect timers
        if self.strength_timer > 0:
            self.strength_timer -= 1
        else:
            self.attack_bonus = self.base_attack_bonus
        if self.knockback_timer > 0:
            self.knockback_timer -= 1
        else:
            self.knockback_boost = 1.0
        
        # smooth horizontal movement with acceleration/deceleration
        target_vel_x = 0
        moving = False
        if keys[pygame.K_a]:
            target_vel_x = -self.speed if self.dash_timer == 0 else 0
            self.facing = -1
            moving = True
        if keys[pygame.K_d]:
            target_vel_x = self.speed if self.dash_timer == 0 else 0
            self.facing = 1
            moving = True
        
        # smoothly interpolate velocity
        self.vel_x += (target_vel_x - self.vel_x) * 0.15
        self.rect.x += self.vel_x

        # jump
        on_ground = self.on_ground(plats)
        if on_ground and not self.on_ground_last:
            self.land_time = 5  # brief land recovery
            # landing particles
            for _ in range(3):
                vx = random.uniform(-1, 1)
                vy = random.uniform(-1, 0.5)
                particles.add(Particle(self.rect.centerx, self.rect.bottom, vx, vy, BLUE, 15))
        self.on_ground_last = on_ground

        # Jump only when on the ground (edge-triggered) to prevent mid-air jumps
        jump_now = keys[pygame.K_w] and not self.jump_held_last
        if jump_now and on_ground:
            self.vel_y = -self.jump
            self.jumps = 1
        # remember held state for next frame
        self.jump_held_last = bool(keys[pygame.K_w])

        # prevent going off top/bottom of screen
        if self.rect.top < 0:
            self.rect.top = 0
            self.vel_y = 0
        elif self.rect.bottom > HEIGHT:
            self.rect.bottom = HEIGHT
            self.vel_y = 0

        # start dash when X pressed and not cooling down
        if keys[pygame.K_x] and self.dash_cd == 0 and self.dash_timer == 0:
            self.dash_timer = 12
            self.dash_vel = self.dash_strength * self.facing
            self.dash_cd = 60
            self.invuln = self.dash_invuln
            game_state.screen_shake = 3
            game_state.screen_shake_intensity = 2

        # apply dash movement (clamp to level bounds after moving)
        if self.dash_timer > 0:
            self.rect.x += int(self.dash_vel)
            # clamp so dash can't push you outside the level
            self.rect.x = max(0, min(self.rect.x, LEVEL_WIDTH - self.rect.width))
            # light friction
            self.dash_vel *= 0.92
            self.dash_timer -= 1
            if self.dash_timer == 0:
                self.dash_vel = 0
                # reset jumps after finishing a dash so player can jump again
                self.jumps = 0

        # reduce cooldowns
        if self.dash_cd > 0:
            self.dash_cd -= 1
        if self.invuln > 0:
            self.invuln -= 1
        if self.land_time > 0:
            self.land_time -= 1

        # gravity
        self.vel_y += 0.6
        self.rect.y += self.vel_y
        for p in plats:
            if self.rect.colliderect(p.rect) and self.vel_y >= 0:
                self.rect.bottom = p.rect.top
                self.vel_y = 0
                # reset jump counter when landing
                self.jumps = 0

        # attack: Mage has a short cast animation before firing; others do melee swing
        if keys[pygame.K_z] and self.att_cd == 0:
            if self.class_name.lower().startswith('mag'):
                # start casting (if not already casting)
                if self.cast_timer == 0:
                    self.cast_timer = 10  # cast duration in frames
                    self.att_cd = 25
            else:
                swing = SwordSwing(self)
                swings.add(swing)
                self.att_cd = 25
        if self.att_cd > 0:
            self.att_cd -= 1

        # handle mage cast timer: spawn projectile at mid-cast with visual flash
        if self.cast_timer > 0:
            # spawn particle flash and bolt at mid-point
            mid_point = 4
            if self.cast_timer == mid_point:
                # spawn slight muzzle flash particle at player's hand
                hand_x = self.rect.centerx + self.facing * (self.rect.width // 2)
                hand_y = self.rect.centery - int(6 * self.scale)
                for _ in range(6):
                    vx = random.uniform(-1.5, 1.5) + self.facing * 0.5
                    vy = random.uniform(-1, -0.2)
                    particles.add(Particle(hand_x, hand_y, vx, vy, CYAN, lifetime=12))
                # spawn the projectile
                bolt = MagicBolt(self)
                swings.add(bolt)
            self.cast_timer -= 1

        # animation phase for walking: only advance when actually moving horizontally
        if abs(self.vel_x) > 0.2:
            self.walk_phase = (self.walk_phase + 1) % 30
        else:
            self.walk_phase = 0

    def on_ground(self, plats):
        # Consider the player on-ground when their bottom is very close to a platform's top
        # and the player's horizontal center is above that platform.
        # Use a small tolerance to allow for minor positional differences (e.g., 6 pixels).
        tol = 6
        for p in plats:
            top = p.rect.top
            if (top - tol) <= self.rect.bottom <= (top + tol) and (p.rect.left < self.rect.centerx < p.rect.right):
                return True
        return False

    def draw(self, s):
        self.draw_at_pos(s, self.rect)
        
    def draw_at_pos(self, s, rect):
        # Render character to a temporary surface
        x, y = rect.topleft
        bob = 0
        if self.walk_phase:
            bob = int(math.sin(self.walk_phase / 5.0) * 2 * self.scale)
        
        surf_w = rect.width
        surf_h = rect.height
        char_surf = pygame.Surface((surf_w, surf_h), pygame.SRCALPHA)
        
        # Character drawing with proper centering
        # Head
        head_w = int(16 * self.scale)
        head_h = int(14 * self.scale)
        head_x = int((surf_w - head_w) / 2)
        head_y = int(4 * self.scale) + bob
        
        head_color = (200, 160, 120)
        pygame.draw.ellipse(char_surf, head_color, (head_x, head_y, head_w, head_h))
        # Hair
        pygame.draw.rect(char_surf, (40, 30, 20), (head_x, head_y, head_w, int(5*self.scale)))
        # Eyes
        eye_color = (30, 30, 100)
        eye_left_x = head_x + int(4 * self.scale)
        eye_right_x = head_x + int(12 * self.scale)
        eye_y = head_y + int(5 * self.scale)
        pygame.draw.circle(char_surf, eye_color, (int(eye_left_x), int(eye_y)), int(1.5*self.scale))
        pygame.draw.circle(char_surf, eye_color, (int(eye_right_x), int(eye_y)), int(1.5*self.scale))
        pygame.draw.circle(char_surf, WHITE, (int(eye_left_x + 0.3*self.scale), int(eye_y - 0.3*self.scale)), int(0.7*self.scale))
        pygame.draw.circle(char_surf, WHITE, (int(eye_right_x + 0.3*self.scale), int(eye_y - 0.3*self.scale)), int(0.7*self.scale))
        
        # Torso
        torso_w = int(18 * self.scale)
        torso_h = int(22 * self.scale)
        torso_x = int((surf_w - torso_w) / 2)
        torso_y = head_y + head_h + bob
        
        torso_color = (60, 100, 160)
        pygame.draw.rect(char_surf, torso_color, (torso_x, torso_y, torso_w, torso_h))
        # Armor stripe
        pygame.draw.rect(char_surf, (100, 140, 200), (torso_x + int(7*self.scale), torso_y, int(4*self.scale), torso_h))
        
        # Arms
        arm_w = int(7 * self.scale)
        arm_h = int(4 * self.scale)
        arm_y = torso_y + int(4 * self.scale) + bob
        arm_left_x = torso_x - arm_w - int(2*self.scale)
        arm_right_x = torso_x + torso_w + int(2*self.scale)
        
        pygame.draw.rect(char_surf, head_color, (arm_left_x, arm_y, arm_w, arm_h))
        pygame.draw.rect(char_surf, head_color, (arm_right_x, arm_y, arm_w, arm_h))
        
        # Legs
        leg_w = int(6 * self.scale)
        leg_h = int(14 * self.scale)
        leg_color = (40, 40, 60)
        leg_left_x = torso_x + int(2*self.scale)
        leg_right_x = torso_x + int(10*self.scale)
        leg_y = torso_y + torso_h + bob
        
        pygame.draw.rect(char_surf, leg_color, (leg_left_x, leg_y, leg_w, leg_h))
        pygame.draw.rect(char_surf, leg_color, (leg_right_x, leg_y, leg_w, leg_h))
        
        # Health bar drawn on main surface (not rotated)
        pygame.draw.rect(s, GRAY, (rect.x, rect.y - 8, 40, 5))
        pygame.draw.rect(s, RED, (rect.x, rect.y - 8, 40 * (self.health / self.max_health), 5))

        # Dash visuals: enhanced motion blur and speed effect
        if self.dash_timer > 0:
            # compute progress of dash (0..1)
            dash_prog = max(0.0, min(1.0, (12 - self.dash_timer) / 12.0))
            
            # Draw smoother speed streaks behind the character with easing
            streak_color = (150, 200, 255)
            for i in range(1, 6):
                t = i / 6.0
                opacity = int(200 * (1 - dash_prog) * (1 - t))
                offset = int(self.dash_vel * 0.06 * (i) * (1 - dash_prog))
                start_x = rect.centerx - offset * self.facing
                pygame.draw.line(s, streak_color, 
                                (start_x, rect.centery - int(12*self.scale) - i),
                                (start_x - int(28*self.scale) * self.facing, rect.centery + int(12*self.scale) + i),
                                max(1, int(1 + (1 - t) * self.scale)))
            
            # Lean angle when dashing (smoother easing)
            lean = int(24 * (1 - (self.dash_timer / 12.0)) * (1 - 0.3 * math.sin(dash_prog * math.pi * 2)))
            angle = -lean if self.facing == 1 else lean
            rotated = pygame.transform.rotate(char_surf, angle)
            
            # draw layered motion blur afterimages for depth
            for i in range(3):
                t = (i + 1) / 4.0
                alpha = int(120 * (1 - t) * (1 - dash_prog))
                trail = rotated.copy()
                trail.fill((120, 200, 255, alpha), special_flags=pygame.BLEND_RGBA_MULT)
                tx = rect.x - int(self.dash_vel * 0.04 * (i+1.2) * self.facing)
                ty = rect.y - int(i * 2 * (1 - dash_prog))
                s.blit(trail, (tx - (rotated.get_width() - surf_w)//2, ty - (rotated.get_height() - surf_h)//2))
            
            # Glow effect at dash point
            glow_size = int(20 * self.scale * (1 - dash_prog))
            glow = pygame.Surface((glow_size*2, glow_size*2), pygame.SRCALPHA)
            pygame.draw.circle(glow, (150, 200, 255, 100), (glow_size, glow_size), glow_size)
            s.blit(glow, (rect.centerx - glow_size, rect.centery - glow_size))
            
            # Finally blit rotated main character
            s.blit(rotated, (rect.x - (rotated.get_width() - surf_w)//2, rect.y - (rotated.get_height() - surf_h)//2))
        else:
            # normal draw
            s.blit(char_surf, (x, y))

class Enemy(pygame.sprite.Sprite):
    def __init__(self,x,y):
        super().__init__()
        # scale enemy size with CHAR_SCALE
        ew = int(32 * CHAR_SCALE)
        eh = int(48 * CHAR_SCALE)
        self.image = pygame.Surface((ew, eh), pygame.SRCALPHA)
        
        # Draw bandit: red body, black mask/bandana, menacing look
        # Body (red shirt)
        pygame.draw.rect(self.image, (200, 40, 40), (int(4*CHAR_SCALE), int(16*CHAR_SCALE), int(24*CHAR_SCALE), int(20*CHAR_SCALE)))
        
        # Head (tan/skin color)
        pygame.draw.ellipse(self.image, (180, 150, 120), (int(6*CHAR_SCALE), int(2*CHAR_SCALE), int(20*CHAR_SCALE), int(14*CHAR_SCALE)))
        
        # Black bandit mask covering eyes
        pygame.draw.rect(self.image, BLACK, (int(8*CHAR_SCALE), int(4*CHAR_SCALE), int(16*CHAR_SCALE), int(6*CHAR_SCALE)))
        
        # Eyes (white with menacing pupils)
        pygame.draw.circle(self.image, WHITE, (int(12*CHAR_SCALE), int(7*CHAR_SCALE)), int(2*CHAR_SCALE))
        pygame.draw.circle(self.image, WHITE, (int(20*CHAR_SCALE), int(7*CHAR_SCALE)), int(2*CHAR_SCALE))
        pygame.draw.circle(self.image, BLACK, (int(12*CHAR_SCALE), int(7*CHAR_SCALE)), int(1*CHAR_SCALE))
        pygame.draw.circle(self.image, BLACK, (int(20*CHAR_SCALE), int(7*CHAR_SCALE)), int(1*CHAR_SCALE))
        
        # Arms (tan)
        pygame.draw.rect(self.image, (180, 150, 120), (int(2*CHAR_SCALE), int(16*CHAR_SCALE), int(5*CHAR_SCALE), int(14*CHAR_SCALE)))
        pygame.draw.rect(self.image, (180, 150, 120), (int(25*CHAR_SCALE), int(16*CHAR_SCALE), int(5*CHAR_SCALE), int(14*CHAR_SCALE)))
        
        # Legs (black pants)
        pygame.draw.rect(self.image, BLACK, (int(8*CHAR_SCALE), int(36*CHAR_SCALE), int(8*CHAR_SCALE), int(12*CHAR_SCALE)))
        pygame.draw.rect(self.image, BLACK, (int(16*CHAR_SCALE), int(36*CHAR_SCALE), int(8*CHAR_SCALE), int(12*CHAR_SCALE)))
        
        self.rect = self.image.get_rect(topleft=(x,y))
        self.health=60; self.max_health=60
        self.speed=2; self.dir=1; self.cool=0
        self.facing=1
        self.vel_y = 0.0
        self.knockback_x = 0.0
        self.hit_flash_timer = 0  # Flash when hit by sword
        
    def ai(self,player,plats,swings,particles):
        # knockback friction
        self.knockback_x *= 0.90
        self.rect.x += self.knockback_x
        
        if abs(player.rect.centerx - self.rect.centerx)<120:
            if self.cool==0:
                swing = SwordSwing(self); swings.add(swing)
                self.cool=40
            self.facing = 1 if player.rect.centerx > self.rect.centerx else -1
        else:
            self.rect.x += self.speed*self.dir
            # clamp to level bounds so bandits cannot run off the map
            self.rect.x = max(0, min(self.rect.x, LEVEL_WIDTH - self.rect.width))
            self.facing = self.dir
            if random.random()<0.01: self.dir*=-1
        self.vel_y += 0.6
        self.rect.y += self.vel_y
        for p in plats:
            if self.rect.colliderect(p.rect) and self.vel_y>=0:
                self.rect.bottom=p.rect.top
                self.vel_y=0
        if self.cool>0:self.cool-=1
        if self.hit_flash_timer > 0:
            self.hit_flash_timer -= 1
    
    def take_damage(self, dmg, particles):
        """Handle damage and spawn damage particles."""
        self.health -= dmg
        if self.health < 0:
            self.health = 0
        # damage particles
        for _ in range(5):
            vx = random.uniform(-2, 2)
            vy = random.uniform(-3, -1)
            particles.add(Particle(self.rect.centerx, self.rect.centery, vx, vy, RED, 20))
        game_state.screen_shake = 2
        game_state.screen_shake_intensity = 1
        self.hit_flash_timer = 8  # Flash for 8 frames when hit
        
    def draw(self,s):
        self.draw_at_pos(s, self.rect)
        
    def draw_at_pos(self, s, rect):
        s.blit(self.image, rect)
        pygame.draw.rect(s, GRAY, (rect.x, rect.y-8, 40, 5))
        pygame.draw.rect(s, RED, (rect.x, rect.y-8, 40*(self.health/self.max_health), 5))

class Boss(Enemy):
    def __init__(self,x,y):
        super().__init__(x,y)
        bw = int(64 * CHAR_SCALE)
        bh = int(80 * CHAR_SCALE)
        self.image = pygame.Surface((bw, bh), pygame.SRCALPHA)
        
        # Draw Bandit King: larger, more menacing
        # Body (dark red armor-like)
        pygame.draw.rect(self.image, (120, 20, 20), (int(8*CHAR_SCALE), int(20*CHAR_SCALE), int(48*CHAR_SCALE), int(30*CHAR_SCALE)))
        
        # Head (larger)
        pygame.draw.ellipse(self.image, (180, 150, 120), (int(10*CHAR_SCALE), int(2*CHAR_SCALE), int(44*CHAR_SCALE), int(20*CHAR_SCALE)))
        
        # Large menacing mask
        pygame.draw.rect(self.image, BLACK, (int(12*CHAR_SCALE), int(4*CHAR_SCALE), int(40*CHAR_SCALE), int(10*CHAR_SCALE)))
        
        # Eyes (larger, glowing yellow pupils)
        pygame.draw.circle(self.image, WHITE, (int(20*CHAR_SCALE), int(10*CHAR_SCALE)), int(3*CHAR_SCALE))
        pygame.draw.circle(self.image, WHITE, (int(40*CHAR_SCALE), int(10*CHAR_SCALE)), int(3*CHAR_SCALE))
        pygame.draw.circle(self.image, YELLOW, (int(20*CHAR_SCALE), int(10*CHAR_SCALE)), int(2*CHAR_SCALE))
        pygame.draw.circle(self.image, YELLOW, (int(40*CHAR_SCALE), int(10*CHAR_SCALE)), int(2*CHAR_SCALE))
        
        # Crown/spikes on top
        for i in range(3):
            pygame.draw.polygon(self.image, YELLOW, [(int((18+i*10)*CHAR_SCALE), int(0)), (int((20+i*10)*CHAR_SCALE), int(-3*CHAR_SCALE)), (int((22+i*10)*CHAR_SCALE), int(0))])
        
        # Arms (large)
        pygame.draw.rect(self.image, (180, 150, 120), (int(4*CHAR_SCALE), int(20*CHAR_SCALE), int(6*CHAR_SCALE), int(20*CHAR_SCALE)))
        pygame.draw.rect(self.image, (180, 150, 120), (int(54*CHAR_SCALE), int(20*CHAR_SCALE), int(6*CHAR_SCALE), int(20*CHAR_SCALE)))
        
        # Legs
        pygame.draw.rect(self.image, BLACK, (int(16*CHAR_SCALE), int(50*CHAR_SCALE), int(12*CHAR_SCALE), int(20*CHAR_SCALE)))
        pygame.draw.rect(self.image, BLACK, (int(36*CHAR_SCALE), int(50*CHAR_SCALE), int(12*CHAR_SCALE), int(20*CHAR_SCALE)))
        
        self.rect = self.image.get_rect(topleft=(x,y))
        self.health=300; self.max_health=300; self.speed=3
    def ai(self,player,plats,swings,particles):
        self.knockback_x *= 0.90
        self.rect.x += self.knockback_x

        if random.random()<0.02:
            self.dir = 1 if player.rect.centerx>self.rect.centerx else -1
        self.rect.x += self.speed*self.dir
        # clamp boss to level bounds as well
        self.rect.x = max(0, min(self.rect.x, LEVEL_WIDTH - self.rect.width))
        self.facing = self.dir
        if abs(player.rect.centerx-self.rect.centerx)<150 and self.cool==0:
            swing=SwordSwing(self); swings.add(swing); self.cool=25
            self.facing = 1 if player.rect.centerx > self.rect.centerx else -1
        self.vel_y=getattr(self,"vel_y",0)+0.6
        self.rect.y+=self.vel_y
        for p in plats:
            if self.rect.colliderect(p.rect) and self.vel_y>=0:
                self.rect.bottom=p.rect.top
                self.vel_y=0
        if self.cool>0:self.cool-=1

# ---------- story helpers ----------
def story(lines):
    SCREEN.fill(BLACK)
    for i,l in enumerate(lines):
        draw_text_center(l,200+i*40)
    draw_text_center("Press ENTER",HEIGHT-80,24,GRAY)
    pygame.display.flip()
    wait=True
    while wait:
        for e in pygame.event.get():
            if e.type==pygame.QUIT: pygame.quit();sys.exit()
            if e.type==pygame.KEYDOWN and e.key==pygame.K_RETURN: wait=False

def cutscene(title, lines, duration=None, color_scheme=None):
    """Display an animated cinematic cutscene with dramatic effects."""
    import time
    start_time = time.time()
    fade_in_time = 0.7
    display_time = duration if duration else 4.0
    fade_out_time = 0.7
    total_time = fade_in_time + display_time + fade_out_time
    
    # Color scheme: (primary, accent1, accent2)
    if color_scheme is None:
        color_scheme = ((255, 255, 100), (100, 200, 255), (200, 100, 255))  # Gold/Cyan/Purple
    
    # Generate particle effects
    particles = []
    for _ in range(30):
        particles.append({
            'x': random.uniform(0, WIDTH),
            'y': random.uniform(-50, HEIGHT + 50),
            'vx': random.uniform(-1, 1),
            'vy': random.uniform(0.5, 2),
            'life': random.uniform(0.5, 3),
            'color': random.choice(color_scheme)
        })
    
    while True:
        elapsed = time.time() - start_time
        if elapsed > total_time:
            break
        
        # Calculate alpha based on fade phases
        if elapsed < fade_in_time:
            alpha = int(255 * (elapsed / fade_in_time))
        elif elapsed < fade_in_time + display_time:
            alpha = 255
        else:
            remaining = total_time - elapsed
            alpha = int(255 * (remaining / fade_out_time))
        
        # BACKGROUND: Gradient from dark to atmospheric
        for y in range(0, HEIGHT, 20):
            ratio = y / HEIGHT
            r = int(10 + ratio * 30)
            g = int(10 + ratio * 40)
            b = int(20 + ratio * 50)
            color = (r, g, b)
            pygame.draw.line(SCREEN, color, (0, y), (WIDTH, y))
        
        # Animated background pattern - dancing particles
        for i, p in enumerate(particles):
            p['y'] += p['vy']
            p['x'] += p['vx'] + math.sin(elapsed * 2 + i) * 0.5
            p['life'] -= 1.0 / FPS
            
            if p['life'] < 0:
                p['y'] = -50
                p['life'] = random.uniform(2, 3)
                p['x'] = random.uniform(0, WIDTH)
            
            particle_alpha = int(150 * min(1, p['life']) * (alpha / 255.0))
            if particle_alpha > 0:
                pygame.draw.circle(SCREEN, p['color'], (int(p['x']), int(p['y'])), 2)
        
        # Vertical scanning lines for cinematic effect
        for y in range(0, HEIGHT, 8):
            line_alpha = int(30 * (alpha / 255.0))
            scan_offset = int(math.sin(elapsed * 3 + y / 50) * 5)
            pygame.draw.line(SCREEN, (50, 100, 150), (0, y + scan_offset), (WIDTH, y + scan_offset), 1)
        
        # Dynamic glow background
        glow_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        # Pulsing multi-color glow
        glow_r = int(color_scheme[0][0] * 0.4 + math.sin(elapsed * 1.5) * 30)
        glow_g = int(color_scheme[1][1] * 0.4 + math.sin(elapsed * 1.2) * 20)
        glow_b = int(color_scheme[2][2] * 0.4 + math.sin(elapsed * 1.8) * 30)
        glow_surf.fill((glow_r, glow_g, glow_b, int(20 * (alpha / 255.0))))
        SCREEN.blit(glow_surf, (0, 0))
        
        # Vignette effect (dark edges)
        vignette = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        vignette.fill((0, 0, 0, int(80 * (alpha / 255.0))))
        SCREEN.blit(vignette, (0, 0))
        
        # TITLE: Large, glowing, dramatic
        title_bob = math.sin(elapsed * 1.5) * 8
        title_y = int(140 + title_bob)
        
        # Multi-layer glow with expanding rings
        for glow_layer in range(6, 0, -1):
            glow_alpha = int(40 * (1 - glow_layer / 6) * (alpha / 255.0))
            glow_size_offset = glow_layer * 2
            
            glow_title = BIG.render(title, True, color_scheme[0])
            glow_title_alpha = pygame.Surface((glow_title.get_width() + glow_size_offset*2, glow_title.get_height() + glow_size_offset*2), pygame.SRCALPHA)
            glow_title_alpha.fill((0, 0, 0, 0))
            glow_title_alpha.blit(glow_title, (glow_size_offset, glow_size_offset))
            glow_title_alpha.set_alpha(glow_alpha)
            glow_rect = glow_title_alpha.get_rect(center=(WIDTH//2, title_y))
            SCREEN.blit(glow_title_alpha, glow_rect)
        
        # Main title with bright color
        title_surf = BIG.render(title, True, color_scheme[0])
        title_alpha_surf = pygame.Surface(title_surf.get_size(), pygame.SRCALPHA)
        title_alpha_surf.blit(title_surf, (0, 0))
        title_alpha_surf.set_alpha(min(255, alpha + 30))
        SCREEN.blit(title_alpha_surf, (WIDTH//2 - title_surf.get_width()//2, title_y))
        
        # Underline effect
        underline_width = int(title_surf.get_width() * (0.3 + 0.3 * math.sin(elapsed * 2)))
        underline_alpha = int(200 * (alpha / 255.0))
        pygame.draw.line(SCREEN, color_scheme[1], 
                        (WIDTH//2 - underline_width//2, title_y + 60),
                        (WIDTH//2 + underline_width//2, title_y + 60), 3)
        
        # TEXT LINES: Dramatic reveal with wave effect
        for i, line in enumerate(lines):
            # Stagger animation - each line fades in and up
            line_delay = (i * 0.4)
            if elapsed > line_delay:
                line_progress = min(1.0, (elapsed - line_delay) / 0.6)
                line_alpha = int(alpha * line_progress)
                # Slide up effect
                line_y_offset = int((1 - line_progress) * 30)
            else:
                line_alpha = 0
                line_y_offset = 30
            
            line_y = int(310 + i * 70 + math.sin(elapsed * 1.2 + i * 0.8) * 4 + line_y_offset)
            
            # Multiple glow layers for text
            for glow_offset in range(3, 0, -1):
                glow_text = FONT.render(line, True, color_scheme[1])
                glow_text_alpha = pygame.Surface(glow_text.get_size(), pygame.SRCALPHA)
                glow_text_alpha.fill((0, 0, 0, 0))
                glow_text_alpha.blit(glow_text, (0, 0))
                glow_text_alpha.set_alpha(int(line_alpha * 0.2))
                glow_x = WIDTH//2 - glow_text.get_width()//2 + glow_offset
                glow_y = line_y + glow_offset
                SCREEN.blit(glow_text_alpha, (glow_x, glow_y))
            
            # Main text in white
            line_surf = FONT.render(line, True, WHITE)
            line_alpha_surf = pygame.Surface(line_surf.get_size(), pygame.SRCALPHA)
            line_alpha_surf.blit(line_surf, (0, 0))
            line_alpha_surf.set_alpha(line_alpha)
            SCREEN.blit(line_alpha_surf, (WIDTH//2 - line_surf.get_width()//2, line_y))
        
        # SKIP PROMPT: Breathing effect
        skip_alpha = int(180 * (0.5 + 0.5 * math.sin(elapsed * 2.5)) * (alpha / 255.0))
        skip_text = FONT.render("Press SPACE or ENTER to continue", True, (150, 200, 255))
        skip_alpha_surf = pygame.Surface(skip_text.get_size(), pygame.SRCALPHA)
        skip_alpha_surf.blit(skip_text, (0, 0))
        skip_alpha_surf.set_alpha(skip_alpha)
        SCREEN.blit(skip_alpha_surf, (WIDTH//2 - skip_text.get_width()//2, HEIGHT - 70))
        
        pygame.display.flip()
        CLOCK.tick(FPS)
        
        for e in pygame.event.get():
            if e.type==pygame.QUIT:
                pygame.quit(); sys.exit()
            if e.type==pygame.KEYDOWN:
                if e.key==pygame.K_SPACE or e.key==pygame.K_RETURN:
                    return


def choose_class():
    """Display a simple class selection screen and return the chosen class name."""
    opts = ["Werrier", "Ranger", "Mage"]
    sel = 0
    while True:
        SCREEN.fill(BLACK)
        draw_text_center("Choose your class:", 120, 40, WHITE)
        for i,o in enumerate(opts):
            color = YELLOW if i==sel else WHITE
            draw_text_center(f"{i+1}. {o}", 200 + i*50, 32, color)
        draw_text_center("Use UP/DOWN and ENTER to choose", HEIGHT-100, 20, GRAY)
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type==pygame.QUIT:
                pygame.quit(); sys.exit()
            if e.type==pygame.KEYDOWN:
                if e.key==pygame.K_DOWN:
                    sel = (sel + 1) % len(opts)
                if e.key==pygame.K_UP:
                    sel = (sel - 1) % len(opts)
                if e.key==pygame.K_RETURN:
                    return opts[sel]

def duel(player,enemies,plats,swings):
    particles = pygame.sprite.Group()
    while True:
        CLOCK.tick(FPS)
        keys=pygame.key.get_pressed()
        for e in pygame.event.get():
            if e.type==pygame.QUIT: pygame.quit();sys.exit()
            if e.type==pygame.KEYDOWN:
                if e.key==pygame.K_p:
                    if player.use_potion():
                        draw_text_center("You used a Potion!", HEIGHT//2, 24, GREEN)
                        pygame.display.flip(); pygame.time.delay(600)
                    else:
                        draw_text_center("No potions.", HEIGHT//2, 24, RED)
                        pygame.display.flip(); pygame.time.delay(600)
        player.update(keys,plats,swings,particles)
        for en in enemies:
            en.ai(player,plats,swings,particles)
            # In duel mode, keep enemies inside the visible arena so they can't run off-screen
            en.rect.x = max(0, min(en.rect.x, WIDTH - en.rect.width))
        # also clamp player to arena bounds
        player.rect.x = max(0, min(player.rect.x, WIDTH - player.rect.width))
        swings.update()
        particles.update()
        # damage calc (respect swing active window and avoid multiple hits per swing)
        for sw in swings:
            # projectiles won't have damage_active, melee swings will
            if hasattr(sw, 'damage_active') and not sw.damage_active():
                continue
            for en in enemies:
                if sw.owner != en and sw.rect.colliderect(en.rect) and en not in getattr(sw, 'did_hit', set()):
                    # damage amount scales a bit with owner class
                    # Base damage reduced slightly; projectile bonus nerfed
                    dmg = 16
                    if getattr(sw.owner, 'class_name', '').lower().startswith('war'):
                        dmg += 6
                    if getattr(sw, 'is_projectile', False):
                        dmg += 4
                    en.take_damage(dmg, particles)
                    if hasattr(sw, 'did_hit'):
                        sw.did_hit.add(en)
                    # projectiles expire on hit
                    if getattr(sw, 'is_projectile', False):
                        sw.kill()
                    # knockback
                    knockback_dir = 1 if en.rect.centerx > sw.owner.rect.centerx else -1
                    en.knockback_x = knockback_dir * 8
            if sw.owner != player and sw.rect.colliderect(player.rect) and player not in getattr(sw, 'did_hit', set()):
                # if player is hit by enemy swing and not currently invulnerable
                if getattr(player, 'invuln', 0) == 0:
                    player.health -= 12
                    game_state.screen_shake = 3
                    game_state.screen_shake_intensity = 1
                if hasattr(sw, 'did_hit'):
                    sw.did_hit.add(player)
        # cleanup
        for en in enemies.copy():
            if en.health<=0: enemies.remove(en)
        if player.health<=0: return False
        if not enemies: return True
        # draw (no camera offset in duel mode - it's a separate arena)
        shake_x, shake_y = apply_screen_shake()
        SCREEN.fill(SKY)
        for p in plats: 
            SCREEN.blit(p.image, (p.rect.x + shake_x, p.rect.y + shake_y))
        for part in particles:
            part.draw(SCREEN)
        swings.draw(SCREEN)
        player.draw(SCREEN)
        for en in enemies: en.draw(SCREEN)
        pygame.display.flip()

# ---------- main quest ----------
# Create a wide platform for the extended map
LEVEL_WIDTH = WIDTH * 4  # Make the level 4 screens wide
plats=[Platform(0, HEIGHT-40, LEVEL_WIDTH, 40)]  # Extend the ground platform

# player selects class before starting
player_class = choose_class()

# Opening cutscene
cutscene("THE REALM OF 67", [
    "A peaceful kingdom lay in ruins...",
    "The ancient princess of 67 has been kidnapped",
    "by the fearsome BANDIT KING."
], duration=4.0)

cutscene("YOUR QUEST", [
    f"You are a {player_class}.",
    "Gather the mystical 67 Water",
    "to defeat the bandits and save the realm."
], duration=4.0)

player = Player(120, HEIGHT-200, player_class)

story([f"You stand at the entrance to the realm.", "Prepare yourself for battle!", "Press ENTER to begin..."])

# Map exploration: place enemies on the map and allow the player to roam
map_enemies = pygame.sprite.Group()
map_swings = pygame.sprite.Group()
particles = pygame.sprite.Group()
# place bandits spread out across the whole level for traversal
num_bandits = 10
spawn_min_x = WIDTH + 200
spawn_max_x = LEVEL_WIDTH - 300
for i in range(num_bandits):
    # evenly space with some random jitter
    t = i / max(1, num_bandits - 1)
    bx = int(spawn_min_x + t * (spawn_max_x - spawn_min_x) + random.randint(-120, 120))
    bx = max(spawn_min_x, min(bx, spawn_max_x))
    e = Enemy(bx, HEIGHT - 88)
    e.tag = f"Bandit {i+1}"
    map_enemies.add(e)

# place the boss near the far right of the level
boss = Boss(LEVEL_WIDTH - 300, HEIGHT - 140)
boss.tag = "Bandit King"
map_enemies.add(boss)

# Secret portal for alternate ending (appears when player has enough water)
# Portal location: near the end of level but before boss
portal_rect = pygame.Rect(LEVEL_WIDTH - 500, HEIGHT - 200, 60, 120)
portal_water_requirement = 50  # Need 50 water to use portal

# shop area (village at left)
shop_rect = pygame.Rect(40, HEIGHT - 200, 140, 160)
POTION_COST = 20

# helper to draw HUD
def draw_hud():
    # water and potions
    health_potions = sum(1 for it in player.inventory if it.lower()=='health')
    strength_potions = sum(1 for it in player.inventory if it.lower()=='strength')
    knockback_potions = sum(1 for it in player.inventory if it.lower()=='knockback')
    txt = FONT.render(f"Water: {player.water}    H:{health_potions} S:{strength_potions} K:{knockback_potions}", True, WHITE)
    SCREEN.blit(txt, (10,10))
    # class and health
    cl = FONT.render(f"Class: {player.class_name}    HP: {player.health}/{player.max_health}", True, WHITE)
    SCREEN.blit(cl, (10, 36))
    
    # control hints
    controls_hint = FONT.render("Controls: SPACE=Jump  E=Shop  P=Potion  ARROWS=Move", True, (180,180,180))
    SCREEN.blit(controls_hint, (10, HEIGHT - 26))
    
    # proximity hint for shop
    if abs(player.rect.centerx - shop_rect.centerx) < 200:
        shop_hint = FONT.render("Press E to enter shop", True, YELLOW)
        SCREEN.blit(shop_hint, (shop_rect.centerx - 100, shop_rect.top - 50))
    
    # proximity hint for portal
    if abs(player.rect.centerx - portal_rect.centerx) < 250:
        if player.water >= portal_water_requirement:
            portal_hint = FONT.render(f"Press E for Secret Ending (Need {portal_water_requirement} Water)", True, (200, 100, 255))
            SCREEN.blit(portal_hint, (portal_rect.centerx - 150, portal_rect.top - 50))

# main exploration loop
global camera_x
while True:
    CLOCK.tick(FPS)
    keys = pygame.key.get_pressed()
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            pygame.quit(); sys.exit()
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_d:
                # Toggle debug mode
                game_state.debug_mode = not game_state.debug_mode
            if e.key == pygame.K_p:
                # use potion - prioritize health if HP is low, otherwise try health first
                if player.health < player.max_health * 0.5:
                    # HP is low, use health potion
                    if player.use_potion("Health"):
                        draw_text_center("Used Health Potion! +60 HP", HEIGHT//2, 28, GREEN)
                        pygame.display.flip(); pygame.time.delay(700)
                    else:
                        draw_text_center("No Health potions.", HEIGHT//2, 28, RED)
                        pygame.display.flip(); pygame.time.delay(600)
                else:
                    # try any potion
                    if player.use_potion("Health") or player.use_potion("Strength") or player.use_potion("Knockback"):
                        draw_text_center("Used a Potion!", HEIGHT//2, 28, GREEN)
                        pygame.display.flip(); pygame.time.delay(700)
                    else:
                        draw_text_center("No potions.", HEIGHT//2, 28, RED)
                        pygame.display.flip(); pygame.time.delay(600)
            if e.key == pygame.K_e and player.rect.colliderect(shop_rect):
                # open shop menu
                buying = True
                STRENGTH_COST = 60
                KNOCKBACK_COST = 50
                while buying:
                    SCREEN.fill(BLACK)
                    draw_text_center("Village Shop - Buy Potions", 80, 40, WHITE)
                    draw_text_center("1) Health Potion       - Restore 60 HP  (" + str(POTION_COST) + " Water)", 200, 24, GREEN)
                    draw_text_center("2) Strength Potion    - +25 Damage 1s  (" + str(STRENGTH_COST) + " Water)", 250, 24, YELLOW)
                    draw_text_center("3) Knockback Potion   - 1.8x Knockback (" + str(KNOCKBACK_COST) + " Water)", 300, 24, CYAN)
                    draw_text_center("ESC to leave", HEIGHT - 80, 20, GRAY)
                    draw_text_center(f"Your Water: {player.water}", HEIGHT - 40, 20, WHITE)
                    pygame.display.flip()
                    for ev in pygame.event.get():
                        if ev.type==pygame.QUIT: pygame.quit(); sys.exit()
                        if ev.type==pygame.KEYDOWN:
                            if ev.key==pygame.K_ESCAPE:
                                buying=False
                                break
                            if ev.key==pygame.K_1 or ev.key==pygame.K_KP1:
                                if player.water >= POTION_COST:
                                    player.water -= POTION_COST
                                    player.add_item('Health')
                                    draw_text_center("Bought Health Potion!", HEIGHT//2, 24, GREEN)
                                    pygame.display.flip(); pygame.time.delay(700)
                                else:
                                    draw_text_center("Not enough Water.", HEIGHT//2, 24, RED)
                                    pygame.display.flip(); pygame.time.delay(700)
                            if ev.key==pygame.K_2 or ev.key==pygame.K_KP2:
                                if player.water >= STRENGTH_COST:
                                    player.water -= STRENGTH_COST
                                    player.add_item('Strength')
                                    draw_text_center("Bought Strength Potion!", HEIGHT//2, 24, YELLOW)
                                    pygame.display.flip(); pygame.time.delay(700)
                                else:
                                    draw_text_center("Not enough Water.", HEIGHT//2, 24, RED)
                                    pygame.display.flip(); pygame.time.delay(700)
                            if ev.key==pygame.K_3 or ev.key==pygame.K_KP3:
                                if player.water >= KNOCKBACK_COST:
                                    player.water -= KNOCKBACK_COST
                                    player.add_item('Knockback')
                                    draw_text_center("Bought Knockback Potion!", HEIGHT//2, 24, CYAN)
                                    pygame.display.flip(); pygame.time.delay(700)
                                else:
                                    draw_text_center("Not enough Water.", HEIGHT//2, 24, RED)
                                    pygame.display.flip(); pygame.time.delay(700)
    # update world
    player.update(keys, plats, map_swings, particles)
    for me in map_enemies:
        me.ai(player, plats, map_swings, particles)
    map_swings.update()
    particles.update()

    # Check for portal collision - alternate ending
    if player.rect.colliderect(portal_rect) and player.water >= portal_water_requirement:
        cutscene("A STRANGE PORTAL", [
            "You've discovered something extraordinary...",
            "A shimmering gateway appears before you."
        ], duration=3.0, color_scheme=((200, 100, 255), (100, 255, 200), (255, 200, 100)))
        
        story([
            "You step through the mystical portal...",
            "",
            "The realm of 67 begins to shift and change.",
            "Your accumulated 67 Water creates a bridge between worlds.",
            "",
            f"You escape with {player.water} Water to an alternate dimension.",
            "The portal closes behind you forever.",
            "",
            "ALTERNATE ENDING – You became a traveler between worlds!"
        ])
        pygame.quit(); sys.exit()

    # approach detection: start duel when close enough
    engaged = None
    for me in map_enemies:
        if abs(player.rect.centerx - me.rect.centerx) < 100 and abs(player.rect.centery - me.rect.centery) < 60:
            engaged = me
            break
    if engaged is not None:
        # Check if it's the boss
        is_boss_fight = isinstance(engaged, Boss)
        
        if is_boss_fight:
            # Boss encounter cutscene
            cutscene("THE BANDIT KING", [
                "At last, you face the tyrant!",
                "The shadows part to reveal the legendary outlaw...",
                "Victory or death awaits."
            ], duration=3.5)
        
        # transition to duel with only that enemy
        story([f"You approach {getattr(engaged,'tag', 'an enemy')}!"])
        # Reset positions for duel: center player on screen, place enemy to the right
        player.rect.x = WIDTH // 4
        player.rect.y = HEIGHT - 200
        engaged.rect.x = WIDTH - 300
        engaged.rect.y = HEIGHT - 88
        temp_group = pygame.sprite.Group()
        temp_group.add(engaged)
        swings = pygame.sprite.Group()
        win = duel(player, temp_group, plats, swings)
        if not win:
            story(["You were defeated...", "The realm of 67 falls into ruin.", "BAD ENDING"])
            pygame.quit(); sys.exit()
        else:
            # reward for defeating
            if engaged.health <= 0:
                gained = 10 + random.randint(0, 12)
                player.water += gained
                # potion drop chance - random type
                if random.random() < 0.35:
                    potion_types = ['Health', 'Strength', 'Knockback']
                    player.add_item(random.choice(potion_types))
                player.health = min(player.max_health, player.health + 30)
                # remove from map enemies
                if engaged in map_enemies:
                    map_enemies.remove(engaged)
                # show small reward message
                draw_text_center(f"Victory! +{gained} 67 water", HEIGHT//2, 28, YELLOW)
                pygame.display.flip(); pygame.time.delay(900)

    # check victory: if boss removed
    boss_alive = any(isinstance(m, Boss) for m in map_enemies)
    if not boss_alive:
        # Victory cutscene
        cutscene("VICTORY!", [
            "The Bandit King falls...",
            "The darkness lifts from the realm of 67."
        ], duration=3.0)
        
        story([
            "You defeated the Bandit King!",
            "The princess is saved.",
            "The realm of 67 prospers.",
            "GOOD ENDING – You are the richest in the realm with infinite 67 Water!"
        ])
        pygame.quit(); sys.exit()

    # update camera position to follow player
    target_camera_x = player.rect.centerx - WIDTH // 2
    game_state.camera_x += (target_camera_x - game_state.camera_x) * 0.12
    game_state.camera_x = max(0, min(game_state.camera_x, LEVEL_WIDTH - WIDTH))

    # apply screen shake
    shake_x, shake_y = apply_screen_shake()
    
    # draw world
    # Sky gradient
    SCREEN.fill(SKY)
    
    # Draw parallax background mountains (far layer)
    mountain_color1 = (60, 100, 140)
    mountain_color2 = (80, 120, 160)
    parallax_offset = int(game_state.camera_x * 0.2)
    # Left mountain
    mountain1_points = [(0 - parallax_offset, HEIGHT - 150), (300 - parallax_offset, 200), (600 - parallax_offset, HEIGHT - 150)]
    pygame.draw.polygon(SCREEN, mountain_color1, mountain1_points)
    # Right mountain
    mountain2_points = [(WIDTH//2 - parallax_offset, HEIGHT - 100), (WIDTH - parallax_offset, 150), (WIDTH + 300 - parallax_offset, HEIGHT - 100)]
    pygame.draw.polygon(SCREEN, mountain_color2, mountain2_points)
    
    # Draw decorative clouds
    cloud_color = (200, 220, 255)
    for i in range(3):
        cloud_x = (game_state.camera_x * 0.05 + i * 400) % (LEVEL_WIDTH + 200)
        cloud_y = 80 + i * 80
        for j in range(4):
            pygame.draw.circle(SCREEN, cloud_color, (int(cloud_x + j*30), int(cloud_y)), 20)
    
    # draw platforms with camera offset
    for p in plats:
        screen_rect = p.rect.copy()
        screen_rect.x -= game_state.camera_x
        screen_rect.x += shake_x
        screen_rect.y += shake_y
        
        # Draw platform with texture
        SCREEN.blit(p.image, screen_rect)
        
        # Add grass/detail on top of ground platforms
        if screen_rect.top >= HEIGHT - 100:  # Ground level
            for x in range(0, int(screen_rect.width), 30):
                grass_points = [
                    (int(screen_rect.left + x), int(screen_rect.top)),
                    (int(screen_rect.left + x + 8), int(screen_rect.top - 5)),
                    (int(screen_rect.left + x + 15), int(screen_rect.top))
                ]
                pygame.draw.polygon(SCREEN, (40, 120, 40), grass_points)
    
    # draw shop with camera offset
    shop_screen_rect = shop_rect.copy()
    shop_screen_rect.x -= game_state.camera_x
    shop_screen_rect.x += shake_x
    shop_screen_rect.y += shake_y
    pygame.draw.rect(SCREEN, (120,100,80), shop_screen_rect)
    if abs(shop_screen_rect.centerx - WIDTH//2) < WIDTH:  # Only draw text if shop is on screen
        draw_text_center("Village", shop_screen_rect.top + 12, 20, WHITE)
    
    # draw secret portal with camera offset
    portal_screen_rect = portal_rect.copy()
    portal_screen_rect.x -= game_state.camera_x
    portal_screen_rect.x += shake_x
    portal_screen_rect.y += shake_y
    if abs(portal_screen_rect.centerx - WIDTH//2) < WIDTH:  # Only draw if on screen
        # Draw glowing portal effect
        portal_glow = pygame.Surface((portal_screen_rect.width + 20, portal_screen_rect.height + 20), pygame.SRCALPHA)
        frame_time = pygame.time.get_ticks() / 1000.0
        glow_color_r = int(200 + math.sin(frame_time * 3) * 50)
        glow_color_g = int(100 + math.sin(frame_time * 2.5) * 50)
        glow_color_b = int(200 + math.sin(frame_time * 3.5) * 50)
        pygame.draw.circle(portal_glow, (glow_color_r, glow_color_g, glow_color_b, 100), (portal_glow.get_width()//2, portal_glow.get_height()//2), 40)
        SCREEN.blit(portal_glow, (portal_screen_rect.x - 10, portal_screen_rect.y - 10))
        
        # Draw portal rect with gradient effect
        pygame.draw.rect(SCREEN, (150, 50, 200), portal_screen_rect, 3)
        pygame.draw.rect(SCREEN, (200, 100, 255), (portal_screen_rect.x + 5, portal_screen_rect.y + 5, portal_screen_rect.width - 10, portal_screen_rect.height - 10), 2)
        draw_text_center("Portal", portal_screen_rect.centery - 5, 16, (200, 100, 255))
    
    # draw particles, enemies and effects with camera offset
    for part in particles:
        part.rect.x += shake_x
        part.rect.y += shake_y
    particles.draw(SCREEN)
    
    for sw in map_swings:
        sw_rect = sw.rect.copy()
        sw_rect.x -= game_state.camera_x
        sw_rect.x += shake_x
        sw_rect.y += shake_y
        SCREEN.blit(sw.image, sw_rect)
    
    for me in map_enemies:
        screen_rect = me.rect.copy()
        screen_rect.x -= game_state.camera_x
        screen_rect.x += shake_x
        screen_rect.y += shake_y
        me.draw_at_pos(SCREEN, screen_rect)
    
    # draw player with camera offset
    screen_rect = player.rect.copy()
    screen_rect.x -= game_state.camera_x
    screen_rect.x += shake_x
    screen_rect.y += shake_y
    player.draw_at_pos(SCREEN, screen_rect)
    
    draw_hud()
    
    # Show hitboxes when sword is active
    if len(map_swings) > 0 or any(e.hit_flash_timer > 0 for e in map_enemies):
        debug_font = pygame.font.Font(None, 20)
        
        # Draw sword hitboxes (when active)
        for sw in map_swings:
            sw_rect = sw.rect.copy()
            sw_rect.x -= game_state.camera_x
            sw_rect.x += shake_x
            sw_rect.y += shake_y
            pygame.draw.rect(SCREEN, YELLOW, sw_rect, 2)
        
        # Draw enemy hitboxes that are being hit
        for me in map_enemies:
            if me.hit_flash_timer > 0:
                screen_rect = me.rect.copy()
                screen_rect.x -= game_state.camera_x
                screen_rect.x += shake_x
                screen_rect.y += shake_y
                # Draw in bright red when hit
                pygame.draw.rect(SCREEN, (255, 100, 100), screen_rect, 3)
                # Pulsing effect - thicker border when freshly hit
                if me.hit_flash_timer > 4:
                    pygame.draw.rect(SCREEN, RED, screen_rect, 5)
    
    pygame.display.flip()

