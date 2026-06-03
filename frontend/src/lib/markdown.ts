import { marked } from 'marked'

/**
 * GitHub-style slug: lowercase, strip non-word/non-space/non-hyphen chars,
 * replace each space with a hyphen (preserves double-hyphens from "Foo & Bar").
 */
function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^\w\s-]/g, '')
    .replace(/\s/g, '-')
}

/**
 * Parse markdown to HTML and inject id attributes on every heading so that
 * TOC anchor links (e.g. #billing--escrow) resolve correctly.
 * marked v10+ no longer emits heading ids by default.
 */
export function parseMarkdown(md: string): string {
  const html = marked.parse(md) as string
  return html.replace(
    /<(h[1-6])>(.*?)<\/h[1-6]>/g,
    (_match, tag: string, content: string) => {
      const plainText = content.replace(/<[^>]+>/g, '')
      const id = slugify(plainText)
      return `<${tag} id="${id}">${content}</${tag}>`
    },
  )
}
