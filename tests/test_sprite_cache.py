import unittest
import pygame

from genesis.visuals import cell_sprite, predator_sprite


class SpriteCacheTests(unittest.TestCase):
    def test_cache_preserves_pixels_and_reuses_surfaces(self):
        for make in (cell_sprite,predator_sprite):
            make.cache_clear()
            for args in ((0,4,-2,True),(16,15,2,False),(32,52,0,True)):
                cached=make(*args)
                self.assertIs(make(*args),cached)
                self.assertEqual(pygame.image.tostring(cached,'RGBA'),
                                 pygame.image.tostring(make.__wrapped__(*args),'RGBA'))
            self.assertEqual(make.cache_info().hits,3)
            make.cache_clear()

    def test_palette_and_zoom_churn_remain_within_pixel_memory_limit(self):
        for make in (cell_sprite,predator_sprite):
            make.cache_clear()
            for index in range(33):
                for radius in (4,20,96):
                    for pulse in range(-2,3):
                        make(index,radius,pulse,True)
                        info=make.cache_info()
                        self.assertLessEqual(info.currsize,512)
                        self.assertLessEqual(info.bytes,16*1024*1024)
            self.assertLess(make.cache_info().currsize,495)  # Large zoom sprites trigger byte eviction.
            make.cache_clear()
