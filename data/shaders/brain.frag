#version 330

uniform sampler2D surface;
uniform int spawner_spawn_id = 0;

out vec4 f_color;
in vec2 uv;

vec4 lookup_texel(sampler2D tex, ivec2 uv_px) {
    ivec2 tex_size = textureSize(tex, 0);

    // force black for out-of-bounds pixels
    if ((uv_px.x < 0) || (uv_px.y < 0) || (uv_px.x >= tex_size.x) || (uv_px.y >= tex_size.y)) {
        return vec4(0.0, 0.0, 0.0, 0.0);   
    }

    return texture(tex, (uv_px * 1.0 + vec2(0.5, 0.5)) / tex_size);
}

void main() {
    ivec2 tex_size = textureSize(surface, 0).xy;
    ivec2 uv_px = ivec2(tex_size * uv);

    vec4 old_px = lookup_texel(surface, ivec2(uv_px.x, uv_px.y));

    int neighbors = 0;
    int wall_neighbors = 0;
    int dying_neighbors = 0;
    float neighbor_type = 0.0;
    for (int x = -1; x <= 1; x++) {
        for (int y = -1; y <= 1; y++) {
            if ((x != 0) || (y != 0)) {
                vec4 neighbor = lookup_texel(surface, ivec2(uv_px.x + x, uv_px.y + y));
                if ((neighbor.g > 0.75) && (neighbor.r < 251.0 / 255.0)) {
                    // "randomly" pick the neighbor type to source from using an in-place overwriting technique
                    if (mod(uv_px.x, neighbors + 1) == 0) {
                        neighbor_type = neighbor.r;
                    }

                    neighbors++;
                } else if ((abs(neighbor.r - 253.0 / 255.0) < 0.5 / 255.0) && (spawner_spawn_id > 0)) {
                    // spawners should result in random machine type selection
                    neighbor_type = spawner_spawn_id / 255.0;
                    neighbors++;
                } else {
                    if (neighbor.b > 0.5) {
                        wall_neighbors++;
                    }
                    if (neighbor.g > 0.25) {
                        dying_neighbors++;
                    }
                }
            }
        }
    }

    int population = 0;
    for (int x = -7; x <= 7; x++) {
        for (int y = -7; y <= 7; y++) {
            vec4 neighbor = lookup_texel(surface, ivec2(uv_px.x + x, uv_px.y + y));
            if (neighbor.g > 0.75) {
                population++;
            }
        }
    }

    if (old_px.g > 0.75) {
        f_color = vec4(neighbor_type, 0.5, 0.0, 1.0);
    } else if (old_px.g > 0.4) {
        f_color = vec4(0.0, 0.3, 0.0, 1.0);
    } else if (old_px.g > 0.25) {
        f_color = vec4(0.0, 0.0, 0.0, 1.0);
    } else if (neighbors == 2) {
        f_color = vec4(neighbor_type, 1.0, 0.0, 1.0);
    } else {
        f_color = vec4(0.0, 0.0, 0.0, 1.0);
    }

    if (population > 35) {
        f_color = vec4(0.0, 0.0, 0.0, 1.0);
    }

    if (old_px.r >= 251.5 / 255.0) {
        f_color = vec4(old_px.r, 1.0, 0.0, 1.0);
    }
}