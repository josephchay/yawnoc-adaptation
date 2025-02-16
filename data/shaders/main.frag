#version 330

uniform sampler2D surface;
uniform sampler2D hud_surf;
uniform sampler2D noise_tex;
uniform float time;
uniform ivec2 scroll;
uniform vec2 border_discard;
uniform float saturation = 1.0;

out vec4 f_color;
in vec2 uv;

vec4 lookup_texel(sampler2D tex, ivec2 uv_px) {
    ivec2 tex_size = textureSize(tex, 0);
    return texture(tex, (uv_px * 1.0 + vec2(0.5, 0.5)) / tex_size);
}

void main() {
  vec2 uv_range = vec2(1.0 / (1.0 - border_discard.x), 1.0 / (1.0 - border_discard.y));
  vec2 cropped_uv = vec2(uv.x * uv_range.x - (uv_range.x - 1.0) * 0.5, uv.y * uv_range.y - (uv_range.y - 1.0) * 0.5);
  ivec2 tex_size = textureSize(surface, 0).xy;
  ivec2 uv_px = ivec2(tex_size * cropped_uv);

  vec4 base_color = texture(surface, cropped_uv);
  vec4 ui_color = texture(hud_surf, cropped_uv);

  if (base_color.a < 1.0) {
    float noise_v1 = texture(noise_tex, (uv_px + scroll) * 0.01 + vec2(time * 0.062, time * 0.047)).r;
    float noise_v2 = texture(noise_tex, (uv_px + scroll) * 0.02 + vec2(time * -0.013, time * -0.0485)).r;
    float noise_v = noise_v1 * 0.5 + noise_v2 * 0.5;
    float land_strength = 0.0;
    for (int i = 0; i < 6; i++) {
      if (lookup_texel(surface, uv_px + ivec2(0, -i)).a > 0.9) {    
        land_strength += 0.3;
      }
    }
    noise_v += land_strength * 0.16;
    //f_color = vec4(0.29, 0.612, 0.875, 1.0);
    f_color = vec4(0.447, 0.851, 0.937, 1.0);
    if (noise_v > 0.61) {
      //f_color = vec4(0.447, 0.851, 0.937, 1.0);
      f_color = vec4(0.996, 0.988, 0.827, 1.0);
    } else if (noise_v1 * 0.7 + noise_v2 * 0.3 < 0.45) {
      f_color = vec4(0.29, 0.612, 0.875, 1.0);
    }
  } else {
    f_color = vec4(base_color.rgb, 1.0);
  }

  f_color = f_color * (1.0 - ui_color.a) + vec4(ui_color.rgb * ui_color.a, 1.0);

  if ((cropped_uv.x < 0.0) ||(cropped_uv.x > 1.0) || (cropped_uv.y < 0.0) ||(cropped_uv.y > 1.0)) {
    f_color = vec4(0.0, 0.0, 0.0, 1.0);
  }

  float brightness = (f_color.r + f_color.g + f_color.b) / 3;
  vec3 grayscale_color = vec3(brightness);
  if (f_color.rgb != vec3(1.0, 0.0, 1.0)) {
    f_color = vec4(f_color.rgb * saturation + grayscale_color * (1.0 - saturation), f_color.a);
  }
}