import sys
import random
import math
import pygame
from OpenGL.GL import *
from OpenGL.GL.shaders import compileProgram, compileShader

#роздільна здатність вікна
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600

VERTEX_SHADER = """
#version 330 core
layout (location = 0) in vec2 aPos;

uniform vec2 u_position;
uniform vec2 u_scale;

void main()
{
    
    vec2 pos = aPos * u_scale + u_position;
    gl_Position = vec4(pos, 0.0, 1.0);
}
"""

FRAGMENT_SHADER = """
#version 330 core
out vec4 FragColor;

uniform vec3 u_color;

void main()
{
    FragColor = vec4(u_color, 1.0);
}
"""



class ArkanoidGame:
    def __init__(self):
        pygame.init()
        pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.OPENGL | pygame.DOUBLEBUF)
        pygame.display.set_caption("Arkanoid with Power-ups - OpenGL / Python")

        self.shader = compileProgram(
            compileShader(VERTEX_SHADER, GL_VERTEX_SHADER),
            compileShader(FRAGMENT_SHADER, GL_FRAGMENT_SHADER),
        )

        vertices = [
            0.0, 1.0,
            1.0, 0.0,
            0.0, 0.0,

            0.0, 1.0,
            1.0, 1.0,
            1.0, 0.0
        ]

        self.quad_vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self.quad_vbo)
        glBufferData(GL_ARRAY_BUFFER, sizeof(GLfloat) * len(vertices), (GLfloat * len(vertices))(*vertices), GL_STATIC_DRAW)

        self.quad_vao = glGenVertexArrays(1)
        glBindVertexArray(self.quad_vao)
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 2 * sizeof(GLfloat), ctypes.c_void_p(0))

        self.score = 0
        self.game_started = False
        self.bricks_destroyed_count = 0


        #ракетка
        self.paddle_width = 0.3
        self.paddle_height = 0.04
        self.paddle_x = -self.paddle_width / 2
        self.paddle_y = -0.85
        self.paddle_speed = 0.02

        #мячі
        self.ball_size = 0.04
        self.ball_radius = self.ball_size / 2
        self.balls = [{'x': 0.0, 'y': 0.0, 'vx': random.choice([0.01]), 'vy': 0.015}]

        #цеглини та бонуси
        self.bricks = []
        self.power_ups = [] #список активних падаючих бонусів
        self.init_bricks()

        self.clock = pygame.time.Clock()


    def init_bricks(self):
        self.bricks = []
        rows = 8
        cols = 8
        brick_width = 0.22
        brick_height = 0.05
        gap = 0.02
        start_x = -0.95
        start_y = 0.95

        colors = [
            (0.9, 0.2, 0.2),
            (0.9, 0.4, 0.1),
            (0.9, 0.8, 0.1),
            (0.2, 0.8, 0.2),
            (0.2, 0.6, 0.9),
            (0.5, 0.2, 0.8),
            (0.8, 0.2, 0.6),
            (0.2, 0.8, 0.8)
        ]

        for r in range(rows):
            for c in range(cols):
                bx = start_x + c * (brick_width + gap)
                by = start_y - r * (brick_height + gap)
                self.bricks.append({
                    'x': bx, 'y': by, 'w': brick_width, 'h': brick_height,
                    'color': colors[r], 'active': True
                })

    def reset_ball(self):
        self.game_started = False
        self.balls = [{'x': 0.0, 'y': 0.0, 'vx': random.choice([-0.01, 0.01]), 'vy': 0.015}]\


    def update(self):
        #керування ракеткою
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.paddle_x -= self.paddle_speed
            if self.paddle_x < -1.0:
                self.paddle_x = -1.0
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.paddle_x += self.paddle_speed
            if self.paddle_x + self.paddle_width > 1.0:
                self.paddle_x = 1.0 - self.paddle_width

        #початок гри на пробіл
        if not self.game_started:
            self.balls[0]['x'] = self.paddle_x + self.paddle_width / 2
            self.balls[0]['y'] = self.paddle_y + self.paddle_height + self.ball_radius
            if keys[pygame.K_SPACE]:
                self.game_started = True
                pygame.display.set_caption(f"Arkanoid | Score: {self.score}")
            return

        #рух мяча
        for ball in self.balls[:]:
            ball['x'] += ball['vx']
            ball['y'] += ball['vy']

            #відбивання від стін
            if ball['x'] - self.ball_radius <= -1.0:
                ball['x'] = -1.0 + self.ball_radius
                ball['vx'] = -ball['vx']
            elif ball['x'] + self.ball_radius >= 1.0:
                ball['x'] = 1.0 - self.ball_radius
                ball['vx'] = -(ball['vx'])

            if ball['y'] + self.ball_radius >= 1.0:
                ball['y'] = 1.0 - self.ball_radius
                ball['vy'] = -abs(ball['vy'])

            # падіння конкретного мяча вниз
            if ball['y'] - self.ball_radius <= -1.0:
                self.balls.remove(ball)
                continue

            #колізія з ракеткою
            if (self.paddle_y <= ball['y'] - self.ball_radius <= self.paddle_y + self.paddle_height and
                    self.paddle_x <= ball['x'] <= self.paddle_x + self.paddle_width and
                    ball['vy'] < 0):

                ball['y'] = self.paddle_y + self.paddle_height + self.ball_radius
                ball['vy'] = abs(ball['vy'])


                hit_offset = ball['x'] - (self.paddle_x + self.paddle_width / 2)
                ball['vx'] += hit_offset * 0.03


        #колізія з цеглинами
        for brick in self.bricks:
            if not brick['active']:
                continue

            if (ball['x'] + self.ball_radius > brick['x'] and
                    ball['x'] - self.ball_radius < brick['x'] + brick['w'] and
                    ball['y'] + self.ball_radius > brick['y'] and
                    ball['y'] - self.ball_radius < brick['y'] + brick['h']):

                brick['active'] = False
                ball['vy'] *= -1


                #бали
                self.score += 10
                self.bricks_destroyed_count += 1
                pygame.display.set_caption(f"Arkanoid | Score: {self.score}")

                #цеглини
                if self.bricks_destroyed_count >= 5:
                    self.bricks_destroyed_count = 0

                    for b in self.bricks:
                        if b['active']:
                            b['y'] -= (0.05 + 0.02)

                            if b['y'] <= self.paddle_y + self.paddle_height:
                                self.score = 0
                                self.init_bricks()
                                self.reset_ball()
                                pygame.display.set_caption(f"Arkanoid | Bricks reached bottom! Press SPACE")

                    colors = [
                        (0.9, 0.2, 0.2), (0.9, 0.4, 0.1), (0.9, 0.8, 0.1), (0.2, 0.8, 0.2),
                        (0.2, 0.6, 0.9), (0.5, 0.2, 0.8), (0.8, 0.2, 0.6), (0.2, 0.8, 0.8)
                    ]
                    new_row_color = random.choice(colors)
                    start_x = -0.95
                    top_y = 0.95

                    for c in range(8):
                        bx = start_x + c * (0.22 + 0.02)  # brick_width + gap
                        self.bricks.append({
                            'x': bx, 'y': top_y, 'w': 0.22, 'h': 0.05,
                            'color': new_row_color, 'active': True
                        })

                #випадковий  бонус (50%)
                    if random.random() < 0.5:
                        p_type = random.choice(['expand', 'shrink', 'speed_up'])
                        if p_type == 'expand':
                            p_color = (0.1, 0.9, 0.1)
                        elif p_type == 'shrink':
                            p_color = (0.9, 0.1, 0.1)
                        elif p_type == 'speed_up':
                            p_color = (0.9, 0.6, 0.1)


                        self.power_ups.append({
                            'x': brick['x'] + brick['w'] / 2 - 0.03,
                            'y': brick['y'],
                            'w': 0.06,
                            'h': 0.04,
                            'type': p_type,
                            'color': p_color
                        })
                    break

        if not any(brick['active'] for brick in self.bricks):
            self.init_bricks()

        if len(self.balls) == 0:
                self.score = 0
                self.bricks_destroyed_count = 0
                self.init_bricks()
                self.reset_ball()
                self.power_ups.clear()
                pygame.display.set_caption("Arkanoid | Game Over! Press SPACE to Restart")


        for p in self.power_ups[:]:
            p['y'] -= 0.008

            if (p['x'] < self.paddle_x + self.paddle_width and
                p['x'] + p['w'] > self.paddle_x and
                p['y'] < self.paddle_y + self.paddle_height and
                p['y'] + p['h'] > self.paddle_y):

                if p['type'] == 'expand':
                    self.paddle_width = min(0.5, self.paddle_width + 0.1)
                elif p['type'] == 'shrink':
                    self.paddle_width = max(0.15, self.paddle_width - 0.1)
                elif p['type'] == 'speed_up':
                    for b in self.balls:
                        b['vx'] *= 1.3
                        b['vy'] *= 1.3


                if p in self.power_ups:
                    self.power_ups.remove(p)
            elif p['y'] < -1.0:
                if p in self.power_ups:
                    self.power_ups.remove(p)


    def render(self):
        glClearColor(0.1, 0.1, 0.15, 1.0)
        glClear(GL_COLOR_BUFFER_BIT)

        glUseProgram(self.shader)
        glBindVertexArray(self.quad_vbo)

        #1. цеглини
        for brick in self.bricks:
            if brick['active']:
                glUniform2f(glGetUniformLocation(self.shader, "u_position"), brick['x'], brick['y'])
                glUniform2f(glGetUniformLocation(self.shader, "u_scale"), brick['w'], brick['h'])
                glUniform3f(glGetUniformLocation(self.shader, "u_color"), *brick['color'])
                glDrawArrays(GL_TRIANGLES, 0, 6)

        #2. бонуси
        for p in self.power_ups:
            glUniform2f(glGetUniformLocation(self.shader, "u_position"), p['x'], p['y'])
            glUniform2f(glGetUniformLocation(self.shader, "u_scale"), p['w'], p['h'])
            glUniform3f(glGetUniformLocation(self.shader, "u_color"), *p['color'])
            glDrawArrays(GL_TRIANGLES, 0, 6)

        #3. ракетка
        glUniform2f(glGetUniformLocation(self.shader, "u_position"), self.paddle_x, self.paddle_y)
        glUniform2f(glGetUniformLocation(self.shader, "u_scale"), self.paddle_width, self.paddle_height)
        glUniform3f(glGetUniformLocation(self.shader, "u_color"), 0.2, 0.8, 1.0)
        glDrawArrays(GL_TRIANGLES, 0, 6)

        #4. мячі
        for ball in self.balls[:]:
            ball_draw_x = ball['x'] - self.ball_radius
            ball_draw_y = ball['y'] - self.ball_radius
            glUniform2f(glGetUniformLocation(self.shader, "u_position"), ball_draw_x, ball_draw_y)
            glUniform2f(glGetUniformLocation(self.shader, "u_scale"), self.ball_size, self.ball_size)
            glUniform3f(glGetUniformLocation(self.shader, "u_color"), 1.0, 0.8, 0.2)
            glDrawArrays(GL_TRIANGLES, 0, 6)

        pygame.display.flip()


    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            self.update()
            self.render()
            self.clock.tick(60)

        pygame.quit()
        sys.exit()

if __name__ == '__main__':
    game = ArkanoidGame()
    game.run()