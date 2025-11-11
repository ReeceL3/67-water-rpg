import pygame, sys, random, math
from typing import List
pygame.init()

# ---------- window ----------
WIDTH, HEIGHT = 1280, 720
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("67 Water RPG – Quest for the Princess")
CLOCK = pygame.time.Clock()
FPS = 120

# game state
class GameState:
    def __init__(self):
        self.camera_x = 0.0
        self.screen_shake = 0
        self.screen_shake_intensity = 0

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
        # total life in frames
        self.timer = 12
        # active damage frames
        self.active_start = 3
        self.active_end = 8
        # Draw horizontal sword pointing right
        blade_length = int(50 * CHAR_SCALE)
        blade_w = max(2, int(5 * CHAR_SCALE))
        handle_len = int(10 * CHAR_SCALE)
        handle_w = max(2, int(5 * CHAR_SCALE))
        
        size = int(80 * CHAR_SCALE)
        self.base = pygame.Surface((size, size), pygame.SRCALPHA)
        cx = size // 2
        cy = size // 2
        
        # Draw sword horizontally (for stabbing motion)
        # blade: long thin rectangle
        blade_rect = pygame.Rect(cx, cy - blade_w//2, blade_length, blade_w)
        pygame.draw.rect(self.base, (220,220,230), blade_rect)  # steel blade
        # blade tip (pointed)
        tip = [(cx + blade_length, cy - blade_w//2), (cx + blade_length + int(8*CHAR_SCALE), cy), (cx + blade_length, cy + blade_w//2)]
        pygame.draw.polygon(self.base, (220,220,230), tip)
        # guard
        guard_h = int(12 * CHAR_SCALE)
        pygame.draw.rect(self.base, (150,120,60), (cx - int(2*CHAR_SCALE), cy - guard_h//2, int(4*CHAR_SCALE), guard_h))
        # handle (to the left)
        pygame.draw.rect(self.base, (60,30,10), (cx - int(2*CHAR_SCALE) - handle_len, cy - handle_w//2, handle_len, handle_w))
        # pommel
        pygame.draw.circle(self.base, (180,140,60), (cx - int(2*CHAR_SCALE) - handle_len - int(4*CHAR_SCALE), cy), int(4*CHAR_SCALE))
        # edge highlight on top of blade
        pygame.draw.line(self.base, WHITE, (cx, cy - blade_w//2 + 1), (cx + blade_length, cy - blade_w//2 + 1), max(1, int(1*CHAR_SCALE)))
        
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        self.rect = self.image.get_rect()
        self.facing = getattr(owner, "facing", 1)
        self.owner = owner
        self.did_hit = set()

    def update(self):
        self.timer -= 1
        if self.timer <= 0:
            self.kill()
            return
        # progress 0..1
        life = 12
        prog = max(0.0, min(1.0, (life - self.timer) / life))
        
        # STAB MOTION: extend then retract
        # 0-0.4: extend forward (thrust)
        # 0.4-1.0: retract back
        if prog < 0.4:
            extend = (prog / 0.4) * int(60 * CHAR_SCALE)  # extends up to 60 pixels
        else:
            extend = (1.0 - prog) / 0.6 * int(60 * CHAR_SCALE)  # retracts
        
        # redraw the sword (static orientation, just translate)
        self.image.fill((0,0,0,0))
        size = self.image.get_width()
        self.image.blit(self.base, (0, 0))
        
        # Position: start at owner + base offset, move forward during stab
        base_offset_x = int(32 * CHAR_SCALE) if self.facing == 1 else int(-32 * CHAR_SCALE)
        stab_offset = extend if self.facing == 1 else -extend
        self.rect.center = (self.owner.rect.centerx + base_offset_x + stab_offset, self.owner.rect.centery)

    def damage_active(self):
        life = 12
        elapsed = life - self.timer
        return self.active_start <= elapsed <= self.active_end


class MagicBolt(pygame.sprite.Sprite):
    """Simple projectile used by Mage class."""
    def __init__(self, owner):
        super().__init__()
        self.owner = owner
        self.speed = 18 * owner.facing
        self.image = pygame.Surface((int(12*CHAR_SCALE), int(8*CHAR_SCALE)), pygame.SRCALPHA)
        pygame.draw.ellipse(self.image, (150,180,255), (0,0,self.image.get_width(), self.image.get_height()))
        self.rect = self.image.get_rect(center=(owner.rect.centerx + owner.facing* (owner.rect.width//2 + 10), owner.rect.centery))
        self.life = 40
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

        if keys[pygame.K_w]:
            if on_ground:
                self.vel_y = -self.jump
                self.jumps = 1
            elif self.jumps < self.max_jumps:
                self.vel_y = -self.jump
                self.jumps += 1

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

        # attack: Mage fires projectiles, others do melee swing
        if keys[pygame.K_z] and self.att_cd == 0:
            if self.class_name.lower().startswith('mag'):
                bolt = MagicBolt(self)
                swings.add(bolt)
            else:
                swing = SwordSwing(self)
                swings.add(swing)
            self.att_cd = 25
        if self.att_cd > 0:
            self.att_cd -= 1

        # animation phase for bobbing while walking
        if self.vel_x != 0:
            self.walk_phase = (self.walk_phase + 1) % 30
        else:
            self.walk_phase = 0

    def on_ground(self, plats):
        for p in plats:
            if self.rect.bottom <= p.rect.top + 5 and p.rect.left < self.rect.centerx < p.rect.right:
                return True
        return False

    def draw(self, s):
        self.draw_at_pos(s, self.rect)
        
    def draw_at_pos(self, s, rect):
        # simple procedural 2D character: head + torso + arm, scaled
        x, y = rect.topleft
        bob = 0
        if self.walk_phase:
            bob = int(math.sin(self.walk_phase / 5.0) * 3 * self.scale)
        head_w = int(16 * self.scale)
        head_h = int(14 * self.scale)
        torso_w = int(16 * self.scale)
        torso_h = int(26 * self.scale)
        head_x = x + int(8 * self.scale)
        head_y = y + int(0 * self.scale) + bob
        torso_x = x + int(8 * self.scale)
        torso_y = y + int(14 * self.scale) + bob
        # head
        pygame.draw.ellipse(s, (80, 160, 220), (head_x, head_y, head_w, head_h))
        # torso
        pygame.draw.rect(s, (40, 100, 180), (torso_x, torso_y, torso_w, torso_h))
        # arm
        arm_w = int(10 * self.scale)
        arm_h = int(4 * self.scale)
        if self.facing == 1:
            pygame.draw.rect(s, (80, 160, 220), (x + int(20 * self.scale), y + int(20 * self.scale) + bob, arm_w, arm_h))
        else:
            pygame.draw.rect(s, (80, 160, 220), (x - int(2 * self.scale), y + int(20 * self.scale) + bob, arm_w, arm_h))
        # health bar
        pygame.draw.rect(s, GRAY, (rect.x, rect.y - 8, 40, 5))
        pygame.draw.rect(s, RED, (rect.x, rect.y - 8, 40 * (self.health / self.max_health), 5))
        # dash glow when invulnerable
        if self.invuln > 0:
            a = max(40, int(200 * (self.invuln / 12)))
            glow = pygame.Surface((rect.width * 2, rect.height), pygame.SRCALPHA)
            glow.fill((60, 160, 255, a))
            s.blit(glow, (rect.x - rect.width // 2, rect.y))
        # dash afterimages
        if self.dash_timer > 0:
            for i in range(1,4):
                ta = max(10, int(120 * (1 - i/4)))
                trail = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                trail.fill((60,160,255,ta))
                tx = rect.x - int(self.dash_vel * 0.06 * i)
                s.blit(trail, (tx, rect.y))

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
            self.facing = self.dir
            if random.random()<0.01: self.dir*=-1
        self.vel_y += 0.6
        self.rect.y += self.vel_y
        for p in plats:
            if self.rect.colliderect(p.rect) and self.vel_y>=0:
                self.rect.bottom=p.rect.top
                self.vel_y=0
        if self.cool>0:self.cool-=1
    
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
                    dmg = 18
                    if getattr(sw.owner, 'class_name', '').lower().startswith('war'):
                        dmg += 6
                    if getattr(sw, 'is_projectile', False):
                        dmg += 8
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
player = Player(120, HEIGHT-200, player_class)

story([f"You awaken once more in the realm of 67.", f"You are a {player_class}.", "The princess has been taken by the Bandit King.","Collect the sacred 67 Water and rescue her!"])

# Map exploration: place enemies on the map and allow the player to roam
map_enemies = pygame.sprite.Group()
map_swings = pygame.sprite.Group()
particles = pygame.sprite.Group()
# place bandits spread out far across the level for traversal
bandit_positions = [WIDTH + 500, WIDTH + 1200, WIDTH + 2000]  # Much further to the right
for i, bx in enumerate(bandit_positions, start=1):
    e = Enemy(bx, HEIGHT - 88)
    e.tag = f"Bandit {i}"
    map_enemies.add(e)
# place the boss even further right
boss = Boss(WIDTH + 2500, HEIGHT - 140)  # Boss is far to the right
boss.tag = "Bandit King"
map_enemies.add(boss)

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

# main exploration loop
global camera_x
while True:
    CLOCK.tick(FPS)
    keys = pygame.key.get_pressed()
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            pygame.quit(); sys.exit()
        if e.type == pygame.KEYDOWN:
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

    # approach detection: start duel when close enough
    engaged = None
    for me in map_enemies:
        if abs(player.rect.centerx - me.rect.centerx) < 100 and abs(player.rect.centery - me.rect.centery) < 60:
            engaged = me
            break
    if engaged is not None:
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
    SCREEN.fill(SKY)
    # draw platforms with camera offset
    for p in plats:
        screen_rect = p.rect.copy()
        screen_rect.x -= game_state.camera_x
        screen_rect.x += shake_x
        screen_rect.y += shake_y
        SCREEN.blit(p.image, screen_rect)
    
    # draw shop with camera offset
    shop_screen_rect = shop_rect.copy()
    shop_screen_rect.x -= game_state.camera_x
    shop_screen_rect.x += shake_x
    shop_screen_rect.y += shake_y
    pygame.draw.rect(SCREEN, (120,100,80), shop_screen_rect)
    if abs(shop_screen_rect.centerx - WIDTH//2) < WIDTH:  # Only draw text if shop is on screen
        draw_text_center("Village", shop_screen_rect.top + 12, 20, WHITE)
    
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
    pygame.display.flip()

