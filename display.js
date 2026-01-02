#!/usr/bin/env node

// Source - https://stackoverflow.com/a
// Posted by Nicolas Hoizey
// Retrieved 2025-12-31, License - CC BY-SA 4.0

const fs = require('fs');
const path = require('path');

const ROOT_DIR = path.resolve(__dirname, 'images', 'optimized');
const OUTPUT_FILENAME = 'README.md';
const SKIP_FILENAMES = new Set(['README2.md', OUTPUT_FILENAME]);
const NB_IMAGES_PER_LINE = 4;
let nbImages = 0;
let mdContent = '<table>';

fs.readdirSync(ROOT_DIR).forEach((image) => {
  if (!SKIP_FILENAMES.has(image)) {
    if (!(nbImages % NB_IMAGES_PER_LINE)) {
      if (nbImages > 0) {
        mdContent += `
</tr>`;
      }
      mdContent += `
<tr>`;
    }
    nbImages++;
    mdContent += `
<td valign="bottom">
<img src="./images/optimized/${image}" width="200"><br>
${image}
</td>
`;
  }
});
mdContent += `
${nbImages > 0 ? '</tr>' : ''}</table>`;

fs.writeFileSync(path.resolve(__dirname, OUTPUT_FILENAME), mdContent);
