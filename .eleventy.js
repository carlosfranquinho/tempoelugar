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
