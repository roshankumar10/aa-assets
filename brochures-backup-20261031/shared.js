// Panels shared by all three brochures. Edit copy here once and every brochure picks it up.
// Usage in a page: <div data-include="flap"></div>
(function () {
  const PH = (label) => `<span class="ph-tag">PLACEHOLDER: ${label}</span>`;

  const T = {
    // ---------- OUTSIDE: inner flap (left panel) ----------
    flap: `
      <div class="section">
        <h2>About Atlas</h2>
        <p>Atlas Academy is a technology academy for kids and teens in Richmond and Vancouver.
        Every course is designed and taught by engineers and designers working in the industry today,
        at companies like <strong>EA, IBM and Confluent</strong>.</p>
        <p>Classes are small, so every student gets real time with their instructor. There is no copying
        steps off a screen: students learn why something works, then build it themselves.</p>
      </div>
      <div class="section">
        <h2>Why families choose us</h2>
        <ul class="stars">
          <li><div><strong>Taught by people who do this for a living.</strong>
            Designed and taught by engineers and designers working at EA, IBM and Confluent.</div></li>
          <li><div><strong>They work it out, then build it.</strong>
            No copying steps off a screen. When something breaks, students reason out why and fix it.</div></li>
          <li><div><strong>No homework, no extra screen time.</strong>
            Real learning, done in class. Evenings stay free.</div></li>
        </ul>
      </div>
      <div class="qr">
        <img src="assets/qr-freeworkshops.png" alt="QR code">
        <div><div class="lbl">Scan to book a free workshop</div>
        <div class="sub">See what your child could build before you enrol.</div></div>
      </div>`,

    // ---------- OUTSIDE: back panel (middle) = the one gold block on this side ----------
    contact: `
      <h2>Save your child&rsquo;s spot</h2>
      <p>Classes are kept small, so places fill each term. Reach us today and we&rsquo;ll find the right level for your child.</p>
      <ul class="cta">
        <li><span class="ic">1</span><div><strong>Call or email to enrol</strong>
          +1 (778) 839 0873<br>admin@atlas-academy.ca</div></li>
        <li><span class="ic">2</span><div><strong>Write to us</strong>
          Questions about levels, schedules or fit? Message us at atlas-academy.ca</div></li>
        <li><span class="ic">3</span><div><strong>Free workshops</strong>
          We can host one at your child&rsquo;s school.</div></li>
      </ul>
      <div class="locations">
        <div><strong>Richmond</strong>Sands Plaza, 11020 No 5 Rd, Unit 213<br>Richmond, BC V6W 1K6</div>
        <div><strong>Vancouver</strong>Young Guns Studio, 2239 Oak St<br>Vancouver, BC</div>
        <div><strong>atlas-academy.ca</strong></div>
      </div>`,

    // ---------- Software Engineering level ladder ----------
    ladderSE: `
      <ul class="ladder">
        <li><span class="n">L1</span><div><strong>Intro to Software Engineering</strong>
          LEDs, buttons and buzzers on a Raspberry Pi, in Python.</div></li>
        <li><span class="n">L2</span><div><strong>Interactive Programming and Sensors</strong>
          The Plant Monitor: light, temperature, humidity and soil sensors.</div></li>
        <li><span class="n">L3</span><div><strong>Solving Problems with Algorithms</strong>
          Sorting, grids and objects in their first big project.</div></li>
        <li><span class="n">L4</span><div><strong>Web and Internet Foundations</strong>
          How the internet works, and building for the web.</div></li>
        <li><span class="n">L5</span><div><strong>The Backend</strong>
          Their own social network: accounts, a database and an API.</div></li>
        <li><span class="n">L6</span><div><strong><span class="ph-text">Level 6 title</span></strong>
          Their own AI agent, built from the ground up.</div></li>
      </ul>`,

    // ---------- 3DMA level ladder (titles not in repo yet) ----------
    ladder3D: `
      <ul class="ladder">
        <li><span class="n">L1</span><div><strong><span>Animation Fundamentals</span></strong>
          <span>A Fully Animated Scene</span>
        <li><span class="n">L2</span><div><strong><span class="ph-text">Modelling & Animation Depth</span></strong>
          <span class="ph-text">A short animated piece with their own rigged Character</span></div></li>
        <li><span class="n">L3</span><div><strong><span class="ph-text">VFX & Simulation</span></strong>
          <span class="ph-text">A fully live action shot +3D VFX with real particle physics!</span></div></li>
        <li><span class="n">L4</span><div><strong><span class="ph-text">Open Studio</span></strong>
          <span class="ph-text">Free to Create whatever you want!</span></div></li>
      </ul>`,

    // ---------- Who teaches ----------
    team: `
      <div class="ph-wrap">${PH("confirm photo releases")}
        <img class="photo" style="height:40mm;object-position:50% 30%" src="assets/202602_teamphoto.jpg" alt="The Atlas team"></div>
      <p class="caption">The Atlas team. Engineers and designers from EA, IBM and Confluent.</p>`,

    // ---------- Quote (Miguel) ----------
    quote: `
      <div class="quote ph-wrap">
        <img src="assets/miguel.jpg" alt="Miguel">
        <div><blockquote>&ldquo;<span class="ph-text">Miguel&rsquo;s quote goes here</span>&rdquo;</blockquote>
        <cite>Miguel, Atlas student <span class="ph-text">level / photo release</span></cite></div>
      </div>`,
  };

  document.querySelectorAll("[data-include]").forEach((el) => {
    const html = T[el.dataset.include];
    if (html === undefined) throw new Error("unknown include " + el.dataset.include);
    el.outerHTML = html;
  });
  window.PH = PH;
})();
