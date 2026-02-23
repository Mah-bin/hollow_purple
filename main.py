import cv2
import mediapipe as mp
import numpy as np
import math
import random

class Particle:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.vx = random.uniform(-8, 8)
        self.vy = random.uniform(-8, 8)
        self.color = color
        self.lifetime = random.randint(20, 40)
        self.age = 0
        self.size = random.randint(3, 8)
    
    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.3
        self.age += 1
        return self.age < self.lifetime
    
    def draw(self, frame):
        alpha = 1.0 - (self.age / self.lifetime)
        if alpha > 0:
            overlay = frame.copy()
            cv2.circle(overlay, (int(self.x), int(self.y)), self.size, self.color, -1)
            cv2.addWeighted(overlay, alpha * 0.7, frame, 1 - alpha * 0.7, 0, frame)

class OrbMerger:
    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
            model_complexity=1
        )
        self.mp_draw = mp.solutions.drawing_utils
        
        self.left_orb_pos = None
        self.right_orb_pos = None
        self.purple_orb_pos = None
        self.merged = False
        self.purple_screen = False
        self.purple_screen_alpha = 0
        
        self.throw_start_pos = None
        self.throw_detected = False
        self.merge_cooldown = 0
        self.was_pinched = False
        self.pinch_start_time = 0
        self.flick_threshold = 100
        
        self.expanding = False
        self.expansion_radius = 30
        self.max_expansion_radius = 400
        
        self.orb_radius = 30
        self.merge_distance = 120
        self.throw_distance = 150
        
        self.particles = []
        self.explosion_particles = []
        
    def get_distance(self, pos1, pos2):
        return math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)
    
    def create_particles(self, x, y, color, count=5):
        for _ in range(count):
            self.particles.append(Particle(x, y, color))
    
    def create_explosion_particles(self, x, y, count=100):
        for _ in range(count):
            particle = Particle(x, y, (180, 0, 180))
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(5, 15)
            particle.vx = math.cos(angle) * speed
            particle.vy = math.sin(angle) * speed
            particle.size = random.randint(5, 12)
            particle.lifetime = random.randint(30, 60)
            self.explosion_particles.append(particle)
    
    def draw_orb(self, frame, center, color, radius=None):
        if radius is None:
            radius = self.orb_radius
            
        for i in range(5):
            alpha = 0.4 - (i * 0.08)
            overlay = frame.copy()
            cv2.circle(overlay, center, int(radius + (i * 12)), color, -1)
            cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
        
        cv2.circle(frame, center, int(radius), color, -1)
        
        highlight_pos = (center[0] - radius//3, center[1] - radius//3)
        cv2.circle(frame, highlight_pos, radius//3, (255, 255, 255), -1)
        
        highlight_pos2 = (center[0] + radius//4, center[1] + radius//4)
        cv2.circle(frame, highlight_pos2, radius//5, (200, 200, 200), -1)
        
        return frame
    
    def detect_throw_gesture(self, index_tip, middle_tip):
        if index_tip is None or middle_tip is None:
            return False
        
        distance = self.get_distance(index_tip, middle_tip)
        return distance < 60
    
    def detect_flick_gesture(self, current_pos, is_pinched):
        if is_pinched and not self.was_pinched:
            self.throw_start_pos = current_pos
            return False
        
        if is_pinched and self.was_pinched and self.throw_start_pos:
            distance_moved = self.get_distance(self.throw_start_pos, current_pos)
            if distance_moved > self.flick_threshold:
                return True
        
        if not is_pinched and self.was_pinched:
            self.throw_start_pos = None
        
        return False
    
    def process_frame(self, frame):
        h, w, _ = frame.shape
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb_frame)
        
        left_index_tip = None
        right_index_tip = None
        right_middle_tip = None
        
        if results.multi_hand_landmarks and results.multi_handedness:
            for hand_landmarks, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
                self.mp_draw.draw_landmarks(
                    frame, 
                    hand_landmarks, 
                    self.mp_hands.HAND_CONNECTIONS,
                    self.mp_draw.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
                    self.mp_draw.DrawingSpec(color=(0, 200, 0), thickness=2)
                )
                
                index_tip = hand_landmarks.landmark[8]
                middle_tip = hand_landmarks.landmark[12]
                index_x = int(index_tip.x * w)
                index_y = int(index_tip.y * h)
                middle_x = int(middle_tip.x * w)
                middle_y = int(middle_tip.y * h)
                
                label = handedness.classification[0].label
                
                if label == "Left":
                    right_index_tip = (index_x, index_y)
                    right_middle_tip = (middle_x, middle_y)
                else:
                    left_index_tip = (index_x, index_y)
        
        if not self.merged:
            if left_index_tip:
                self.left_orb_pos = left_index_tip
                self.create_particles(left_index_tip[0], left_index_tip[1], (255, 0, 0), 3)
            if right_index_tip:
                self.right_orb_pos = right_index_tip
                self.create_particles(right_index_tip[0], right_index_tip[1], (0, 0, 255), 3)
            
            if self.left_orb_pos and self.right_orb_pos:
                distance = self.get_distance(self.left_orb_pos, self.right_orb_pos)
                if distance < self.merge_distance:
                    merge_x = (self.left_orb_pos[0] + self.right_orb_pos[0]) // 2
                    merge_y = (self.left_orb_pos[1] + self.right_orb_pos[1]) // 2
                    self.purple_orb_pos = (merge_x, merge_y)
                    self.merged = True
                    self.merge_cooldown = 10
                    self.was_pinched = False
                    self.create_particles(merge_x, merge_y, (180, 0, 180), 20)
                    self.left_orb_pos = None
                    self.right_orb_pos = None
        else:
            if right_index_tip:
                if not self.expanding:
                    self.purple_orb_pos = right_index_tip
                    self.create_particles(right_index_tip[0], right_index_tip[1], (180, 0, 180), 4)
                
                if self.merge_cooldown > 0:
                    self.merge_cooldown -= 1
                
                is_pinched = self.detect_throw_gesture(right_index_tip, right_middle_tip)
                
                if self.merge_cooldown == 0 and not self.expanding:
                    flick_detected = self.detect_flick_gesture(right_index_tip, is_pinched)
                    if flick_detected:
                        self.expanding = True
                        self.expansion_radius = self.orb_radius + 10
                        self.throw_detected = True
                        self.throw_start_pos = None
                
                self.was_pinched = is_pinched
        
        if self.expanding:
            self.expansion_radius += 20
            
            num_particles = int(self.expansion_radius / 10)
            for i in range(num_particles):
                angle = (i / num_particles) * 2 * math.pi
                px = int(self.purple_orb_pos[0] + math.cos(angle) * self.expansion_radius)
                py = int(self.purple_orb_pos[1] + math.sin(angle) * self.expansion_radius)
                if 0 <= px < w and 0 <= py < h:
                    self.create_particles(px, py, (180, 0, 180), 1)
            
            if self.expansion_radius >= self.max_expansion_radius:
                self.purple_screen = True
                self.purple_screen_alpha = 1.0
                self.expanding = False
        
        self.particles = [p for p in self.particles if p.update()]
        for particle in self.particles:
            particle.draw(frame)
        
        self.explosion_particles = [p for p in self.explosion_particles if p.update()]
        for particle in self.explosion_particles:
            particle.draw(frame)
        
        if not self.purple_screen:
            if self.left_orb_pos and not self.merged:
                self.draw_orb(frame, self.left_orb_pos, (255, 0, 0))
            
            if self.right_orb_pos and not self.merged:
                self.draw_orb(frame, self.right_orb_pos, (0, 0, 255))
            
            if self.purple_orb_pos and self.merged:
                orb_size = self.expansion_radius if self.expanding else (self.orb_radius + 10)
                self.draw_orb(frame, self.purple_orb_pos, (128, 0, 128), orb_size)
        
        if self.purple_screen:
            purple_overlay = np.full_like(frame, (128, 0, 128), dtype=np.uint8)
            cv2.addWeighted(purple_overlay, self.purple_screen_alpha, frame, 1 - self.purple_screen_alpha, 0, frame)
        
        if not self.merged and not self.purple_screen:
            pass
        elif self.merged and not self.purple_screen:
            pass
        
        cv2.rectangle(frame, (5, h-35), (350, h-5), (0, 0, 0), -1)
        cv2.putText(frame, "Press 'r' to reset | 'q' to quit", (10, h - 15), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        return frame
    
    def reset(self):
        self.left_orb_pos = None
        self.right_orb_pos = None
        self.purple_orb_pos = None
        self.merged = False
        self.purple_screen = False
        self.purple_screen_alpha = 0
        self.throw_detected = False
        self.merge_cooldown = 0
        self.was_pinched = False
        self.throw_start_pos = None
        self.expanding = False
        self.expansion_radius = 30
        self.particles = []
        self.explosion_particles = []
    
    def run(self):
        cap = cv2.VideoCapture(0)
        
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        cap.set(cv2.CAP_PROP_FPS, 60)
        
        if not cap.isOpened():
            print("Error: Could not open camera")
            return
        
        print("Starting Orb Merger...")
        print("Controls:")
        print("- Show left index finger for blue orb")
        print("- Show right index finger for red orb")
        print("- Bring them together to merge into purple")
        print("- Pinch index & middle fingers together and FLICK forward to throw!")
        print("- Press 'r' to reset, 'q' to quit")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Error: Failed to capture frame")
                break
            
            frame = cv2.flip(frame, 1)
            
            frame = self.process_frame(frame)
            
            cv2.imshow("Hollow Purple - Gesture Control", frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('r'):
                self.reset()
                print("Reset!")
        
        cap.release()
        cv2.destroyAllWindows()
        self.hands.close()


if __name__ == "__main__":
    app = OrbMerger()
    app.run()
