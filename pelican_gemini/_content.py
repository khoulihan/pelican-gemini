"""
Monkeypatches for the Content class in Pelican, which has some assumptions that
it is working with HTML.
"""

import os
import re
import logging
from html import unescape
from urllib.parse import urlparse, urlunparse, urljoin, unquote


logger = logging.getLogger(__name__)


def _get_intrasite_link_regex(self):
    intrasite_link_regex = self.settings['INTRASITE_LINK_REGEX']
    regex = r"(?P<markup>=> )(?P<quote>)(?P<path>{}(?P<value>[\S]*))".format(intrasite_link_regex)
    return re.compile(regex)


# Wrapper around urljoin so that gemini protocol base won't be rejected
def _urljoin(base, url, *args, **kwargs):
    is_gemini = base.startswith('gemini://')
    if is_gemini:
        base = base.replace('gemini://', 'https://')
    result = urljoin(base, url, *args, **kwargs)
    if is_gemini:
        result = result.replace('https://', 'gemini://')
    return result



def _link_replacer(self, siteurl, m):
    what = m.group('what')
    value = urlparse(m.group('value'))
    path = value.path
    origin = m.group('path')

    # urllib.parse.urljoin() produces `a.html` for urljoin("..", "a.html")
    # so if RELATIVE_URLS are enabled, we fall back to os.path.join() to
    # properly get `../a.html`. However, os.path.join() produces
    # `baz/http://foo/bar.html` for join("baz", "http://foo/bar.html")
    # instead of correct "http://foo/bar.html", so one has to pick a side
    # as there is no silver bullet.
    if self.settings['RELATIVE_URLS']:
        joiner = os.path.join
    else:
        joiner = _urljoin

        # However, it's not *that* simple: urljoin("blog", "index.html")
        # produces just `index.html` instead of `blog/index.html` (unlike
        # os.path.join()), so in order to get a correct answer one needs to
        # append a trailing slash to siteurl in that case. This also makes
        # the new behavior fully compatible with Pelican 3.7.1.
        if not siteurl.endswith('/'):
            siteurl += '/'

    # XXX Put this in a different location.
    if what in {'filename', 'static', 'attach'}:
        def _get_linked_content(key, url):
            nonlocal value

            def _find_path(path):
                if path.startswith('/'):
                    path = path[1:]
                else:
                    # relative to the source path of this content
                    path = self.get_relative_source_path(
                        os.path.join(self.relative_dir, path)
                    )
                return self._context[key].get(path, None)

            # try path
            result = _find_path(url.path)
            if result is not None:
                return result

            # try unquoted path
            result = _find_path(unquote(url.path))
            if result is not None:
                return result

            # try html unescaped url
            unescaped_url = urlparse(unescape(url.geturl()))
            result = _find_path(unescaped_url.path)
            if result is not None:
                value = unescaped_url
                return result

            # check if a static file is linked with {filename}
            if what == 'filename' and key == 'generated_content':
                linked_content = _get_linked_content('static_content', value)
                if linked_content:
                    logger.warning(
                        '{filename} used for linking to static'
                        ' content %s in %s. Use {static} instead',
                        value.path,
                        self.get_relative_source_path())
                    return linked_content

            return None

        if what == 'filename':
            key = 'generated_content'
        else:
            key = 'static_content'

        linked_content = _get_linked_content(key, value)
        if linked_content:
            if what == 'attach':
                linked_content.attach_to(self)
            origin = joiner(siteurl, linked_content.url)
            origin = origin.replace('\\', '/')  # for Windows paths.
        else:
            logger.warning(
                "Unable to find '%s', skipping url replacement.",
                value.geturl(), extra={
                    'limit_msg': ("Other resources were not found "
                                  "and their urls not replaced")})
    elif what == 'category':
        origin = joiner(siteurl, Category(path, self.settings).url)
    elif what == 'tag':
        origin = joiner(siteurl, Tag(path, self.settings).url)
    elif what == 'index':
        origin = joiner(siteurl, self.settings['INDEX_SAVE_AS'])
    elif what == 'author':
        origin = joiner(siteurl, Author(path, self.settings).url)
    else:
        logger.warning(
            "Replacement Indicator '%s' not recognized, "
            "skipping replacement",
            what)

    # keep all other parts, such as query, fragment, etc.
    parts = list(value)
    parts[2] = origin
    origin = urlunparse(parts)

    return ''.join((m.group('markup'), m.group('quote'), origin,
                    m.group('quote')))


# Could maybe use the content_object_init signal to perform this patching
# Not sure there is any advantage though
def _patch_content():
    from pelican.contents import Content
    # This method is tied intimately to html. I don't see any legit mechanism
    # to change its behaviour in a plugin, so we have to monkeypatch it.
    Content._get_intrasite_link_regex = _get_intrasite_link_regex
    # This method has a problem in how it joins URLs - urllib doesn't know
    # about gemini, and just ignores the siteurl
    Content._link_replacer = _link_replacer
