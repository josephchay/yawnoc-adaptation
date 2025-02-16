import pygame

PARTNERS = ['jim']

def generate_shadow_anims(game):
    for partner in PARTNERS:
        entity_data = game.e['EntityDB'].configs[partner]
        for anim in list(entity_data.animations):
            anim_copy = entity_data.animations[anim].hard_copy()
            anim_copy_2 = entity_data.animations[anim].hard_copy()
            entity_data.animations[f'{anim}_shadow'] = anim_copy
            entity_data.animations[f'{anim}_light'] = anim_copy_2
            entity_data.config['animations'][f'{anim}_shadow'] = entity_data.config['animations'][anim]
            entity_data.config['animations'][f'{anim}_light'] = entity_data.config['animations'][anim]
            for i, img in enumerate(anim_copy.images):
                anim_copy.images[i] = pygame.mask.from_surface(img).to_surface(setcolor=(38, 27, 46, 255), unsetcolor=(0, 0, 0, 0))
                anim_copy_2.images[i] = pygame.mask.from_surface(img).to_surface(setcolor=(254, 252, 211, 255), unsetcolor=(0, 0, 0, 0))