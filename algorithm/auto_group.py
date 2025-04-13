import math
import global_variables



def check_group(node, neighbor):


    x1, y1, w1=node[0], node[1], node[2]
    x2, y2, w2=neighbor[0], neighbor[1], neighbor[2]
    if x1 == x2 and y1 == y2:
        return True
    half_length=float(global_variables.vehicle_length/2)
    half_width=float(global_variables.vehicle_width/2)
    corners_relative=[
        (half_length, half_width),
        (half_length, -half_width),
        (-half_length, -half_width),
        (-half_length, half_width)
    ]
    node_corners=[
        rotate_point(corners_relative[0], (x1, y1), w1),
        rotate_point(corners_relative[1], (x1, y1), w1),
        rotate_point(corners_relative[2], (x1, y1), w1),
        rotate_point(corners_relative[3], (x1, y1), w1)
    ]
    neighbor_corners=[
        rotate_point(corners_relative[0], (x2, y2), w2),
        rotate_point(corners_relative[1], (x2, y2), w2),
        rotate_point(corners_relative[2], (x2, y2), w2),
        rotate_point(corners_relative[3], (x2, y2), w2)
    ]
    for i in range(4):
        for j in range(4):
            if intersec(node_corners[i], node_corners[(i + 1) % 4], neighbor_corners[j], neighbor_corners[(j + 1) % 4]):
                return True
    return False

def rotate_point(point, center, angle):
    x, y=point
    cx, cy=center
    new_x=cx + x * math.cos(math.radians(angle)) - y * math.sin(math.radians(angle))
    new_y=cy + x * math.sin(math.radians(angle)) + y * math.cos(math.radians(angle))
    return (new_x, new_y)

def intersec(a, b, c, d):
    if not quick_check(a, b, c, d):
        return False
    v1=(a[0] - c[0], a[1] - c[1])
    v2=(a[0] - d[0], a[1] - d[1])
    v3=(a[0] - b[0], a[1] - b[1])
    f1=v3[0] * v1[1] - v3[1] * v1[0]
    f2=v3[0] * v2[1] - v3[1] * v2[0]
    if f1 == 0 or f2 == 0:
        return True
    v1=(c[0] - a[0], c[1] - a[1])
    v2=(c[0] - b[0], c[1] - b[1])
    v3=(c[0] - d[0], c[1] - d[1])
    f3=v3[0] * v1[1] - v3[1] * v1[0]
    f4=v3[0] * v2[1] - v3[1] * v2[0]
    if f3 == 0 or f4 == 0:
        return True

    if f1 * f2 < 0 and f3 * f4 < 0:
        return True
    return False

def quick_check(a, b, c, d):
    if max(a[0], b[0]) < min(c[0], d[0]) or max(c[0], d[0]) < min(a[0], b[0]) or max(a[1], b[1]) < min(c[1], d[1]) or max(c[1], d[1]) < min(a[1], b[1]):
        return False
    return True


# Test
if __name__ == '__main__':
    x1, y1=70532, 112943
    direction1=180

    x2, y2=70743, 112263
    direction2=180
    node1=(x1, y1, direction1)
    node2=(x2, y2, direction2)
    print(check_group(node1, node2))