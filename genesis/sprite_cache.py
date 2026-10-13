"""LRU surfaces bounded by both count and actual pixel-buffer bytes."""
from collections import OrderedDict, namedtuple
from functools import wraps

CacheInfo = namedtuple('CacheInfo', 'hits misses maxsize currsize bytes maxbytes')


def surface_cache(maxsize=512, maxbytes=16*1024*1024):
    def decorate(make):
        entries = OrderedDict()
        hits = misses = used = 0

        @wraps(make)
        def cached(*args, **kwargs):
            nonlocal hits, misses, used
            key = args if not kwargs else (args, tuple(sorted(kwargs.items())))
            if key in entries:
                hits += 1
                entries.move_to_end(key)
                return entries[key][0]
            misses += 1
            surface = make(*args, **kwargs)
            size = surface.get_pitch()*surface.get_height()
            if size <= maxbytes:
                while entries and (len(entries) >= maxsize or used+size > maxbytes):
                    _, (_, removed) = entries.popitem(last=False)
                    used -= removed
                entries[key] = (surface, size)
                used += size
            return surface

        def clear():
            nonlocal hits, misses, used
            entries.clear()
            hits = misses = used = 0

        cached.cache_clear = clear
        cached.cache_info = lambda: CacheInfo(hits, misses, maxsize, len(entries), used, maxbytes)
        return cached
    return decorate
