#version 330

uniform sampler2D surface;

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

float growth(float val) {
    if (val < 0.3) {
        return 0.0;
    } else if (val < 0.55) {
        return (val - 0.3) / 0.25;
    } else {
        return 1.0;
    }
}

void main() {
    ivec2 tex_size = textureSize(surface, 0).xy;
    ivec2 uv_px = ivec2(tex_size * uv);

    vec4 old_px = lookup_texel(surface, ivec2(uv_px.x, uv_px.y));

    int neighbors = 0;
    float neighbor_type = 0.0;
    int neighbor_max = 0;
    for (int x = -1; x <= 1; x++) {
        for (int y = -1; y <= 1; y++) {
            if ((x != 0) || (y != 0)) {
                vec4 neighbor = lookup_texel(surface, ivec2(uv_px.x + x, uv_px.y + y));
                if ((neighbor.r > 0) && (neighbor.r < 254.0 / 255.0)) {
                    neighbor_type = 0.9;
                    
                    neighbors++;
                }
                neighbor_max++;
            }
        }
    }

    int wide_neighbors = 0;
    int wide_neighbor_max = 0;
    for (int x = -12; x <= 12; x++) {
        for (int y = -12; y <= 12; y++) {
            if (((x != 0) || (y != 0)) && (distance(vec2(x, y), vec2(0, 0)) < 12.0)) {
                vec4 neighbor = lookup_texel(surface, ivec2(uv_px.x + x, uv_px.y + y));
                if ((neighbor.r > 0) && (neighbor.r < 254.0 / 255.0)) {
                    neighbor_type = 0.9;
                    
                    wide_neighbors++;
                }
                wide_neighbor_max++;
            }
        }
    }

    float neighbor_r = (neighbors * 1.0) / neighbor_max;
    float wide_neighbor_r = (wide_neighbors * 1.0) / wide_neighbor_max;

    if ((neighbor_r >= 0.5) && (wide_neighbor_r >= 0.26) && (wide_neighbor_r <= 0.46)) {
        f_color = vec4(neighbor_type, neighbor_r, wide_neighbor_r, 1.0);
    } else if ((neighbor_r <= 0.5) && (wide_neighbor_r >= 0.27) && (wide_neighbor_r <= 0.36)) {
        f_color = vec4(neighbor_type, neighbor_r, wide_neighbor_r, 1.0);
    } else {
        f_color = vec4(0.0, 0.0, 0.0, 1.0);
    }

    f_color = f_color.bgra;
}