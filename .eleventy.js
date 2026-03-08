const rssPlugin = require("@11ty/eleventy-plugin-rss");

module.exports = function (eleventyConfig) {
  // RSS plugin
  eleventyConfig.addPlugin(rssPlugin);

  // Pass through assets and CNAME
  eleventyConfig.addPassthroughCopy("src/assets");
  eleventyConfig.addPassthroughCopy("src/CNAME");

  // Posts collection (sorted by date, newest first)
  eleventyConfig.addCollection("posts", function (collectionApi) {
    return collectionApi
      .getFilteredByGlob("src/posts/*.md")
      .sort((a, b) => b.date - a.date);
  });

  // All unique categories across posts
  eleventyConfig.addCollection("categories", function (collectionApi) {
    const posts = collectionApi.getFilteredByGlob("src/posts/*.md");
    const categoriesMap = new Map();
    for (const post of posts) {
      for (const cat of post.data.categories || []) {
        if (!categoriesMap.has(cat)) {
          categoriesMap.set(cat, []);
        }
        categoriesMap.get(cat).push(post);
      }
    }
    // Return array of { name, slug, posts } sorted by name
    const slugify = (s) => s.toLowerCase()
      .normalize("NFD").replace(/[\u0300-\u036f]/g, "")
      .replace(/\s+/g, "-").replace(/[^a-z0-9-]/g, "");
    return Array.from(categoriesMap.entries())
      .map(([name, posts]) => ({ name, slug: slugify(name), posts: posts.sort((a, b) => b.date - a.date) }))
      .sort((a, b) => a.name.localeCompare(b.name, "pt"));
  });

  // Date filter in Portuguese
  eleventyConfig.addFilter("ptDate", function (date) {
    return new Date(date).toLocaleDateString("pt-PT", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  });

  // ISO date filter for datetime attribute
  eleventyConfig.addFilter("isoDate", function (date) {
    return new Date(date).toISOString().split("T")[0];
  });

  // Limit filter for collections
  eleventyConfig.addFilter("limit", function (arr, n) {
    return arr.slice(0, n);
  });

  // Absolute URL filter
  eleventyConfig.addFilter("absoluteUrl", function (url, base) {
    return new URL(url, base).href;
  });

  // Slug filter (remove accents, lowercase, hyphenate)
  eleventyConfig.addFilter("slug", function (str) {
    return str.toLowerCase()
      .normalize("NFD").replace(/[\u0300-\u036f]/g, "")
      .replace(/\s+/g, "-").replace(/[^a-z0-9-]/g, "");
  });

  return {
    dir: {
      input: "src",
      output: "_site",
      includes: "_includes",
      data: "_data",
    },
    markdownTemplateEngine: "njk",
    htmlTemplateEngine: "njk",
  };
};
