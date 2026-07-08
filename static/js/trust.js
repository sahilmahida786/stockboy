/**
 * ════════════════════════════════════════════════════════════════
 *  STOCKBOY PREMIUM — TRUST SYSTEM JS
 *  Handles Counter Animations and Carousel Swipe logic
 * ════════════════════════════════════════════════════════════════
 */

document.addEventListener('DOMContentLoaded', () => {
  initCounters();
  initCarousel();
});

/* ── 1. ANIMATED COUNTERS ── */
function initCounters() {
  const counters = document.querySelectorAll('.sb-counter-val');
  if (counters.length === 0) return;

  const observerOptions = {
    threshold: 0.5,
    rootMargin: "0px 0px -50px 0px"
  };

  const observer = new IntersectionObserver((entries, obs) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const target = entry.target;
        const endVal = parseFloat(target.getAttribute('data-target'));
        const duration = 2000; // 2 seconds
        const frameRate = 1000 / 60;
        const totalFrames = Math.round(duration / frameRate);
        let frame = 0;

        const isDecimal = target.getAttribute('data-target').includes('.');
        const suffix = target.getAttribute('data-suffix') || '';

        const counterInterval = setInterval(() => {
          frame++;
          // easeOutExpo
          const progress = frame === totalFrames ? 1 : 1 - Math.pow(2, -10 * frame / totalFrames);
          const currentVal = endVal * progress;

          if (isDecimal) {
            target.textContent = currentVal.toFixed(1) + suffix;
          } else {
            target.textContent = Math.round(currentVal) + suffix;
          }

          if (frame === totalFrames) {
            clearInterval(counterInterval);
            target.textContent = (isDecimal ? endVal.toFixed(1) : endVal) + suffix;
          }
        }, frameRate);

        obs.unobserve(target);
      }
    });
  }, observerOptions);

  counters.forEach(counter => observer.observe(counter));
}

/* ── 2. CAROUSEL ── */
function initCarousel() {
  const track = document.getElementById('sbTrustTrack');
  if (!track) return;

  const slides = Array.from(track.children);
  const nextBtn = document.getElementById('sbCarouselNext');
  const prevBtn = document.getElementById('sbCarouselPrev');
  const dotsNav = document.getElementById('sbCarouselDots');
  
  if (slides.length === 0) return;

  let currentIndex = 0;
  let autoPlayInterval;
  let startX = 0;
  let currentX = 0;
  let isDragging = false;
  
  // Calculate items per view based on CSS
  function getItemsPerView() {
    return window.innerWidth >= 769 ? 3 : 1;
  }

  // Create Dots
  if (dotsNav) {
    dotsNav.innerHTML = '';
    slides.forEach((_, idx) => {
      const dot = document.createElement('button');
      dot.className = `sb-carousel-dot ${idx === 0 ? 'active' : ''}`;
      dot.setAttribute('aria-label', `Go to slide ${idx + 1}`);
      dot.addEventListener('click', () => goToSlide(idx));
      dotsNav.appendChild(dot);
    });
  }

  const dots = Array.from(document.querySelectorAll('.sb-carousel-dot'));

  function updateCarousel() {
    const itemsPerView = getItemsPerView();
    // Prevent scrolling past the end
    if (currentIndex > slides.length - itemsPerView) {
      currentIndex = slides.length - itemsPerView;
    }
    if (currentIndex < 0) currentIndex = 0;

    const slideWidth = slides[0].getBoundingClientRect().width;
    track.style.transform = `translateX(-${currentIndex * slideWidth}px)`;

    dots.forEach((dot, idx) => {
      dot.classList.toggle('active', idx === currentIndex);
    });
  }

  function goToSlide(index) {
    currentIndex = index;
    updateCarousel();
    resetAutoPlay();
  }

  function nextSlide() {
    const itemsPerView = getItemsPerView();
    if (currentIndex >= slides.length - itemsPerView) {
      currentIndex = 0;
    } else {
      currentIndex++;
    }
    updateCarousel();
  }

  function prevSlide() {
    const itemsPerView = getItemsPerView();
    if (currentIndex <= 0) {
      currentIndex = slides.length - itemsPerView;
    } else {
      currentIndex--;
    }
    updateCarousel();
  }

  if (nextBtn) {
    nextBtn.addEventListener('click', () => { nextSlide(); resetAutoPlay(); });
  }
  if (prevBtn) {
    prevBtn.addEventListener('click', () => { prevSlide(); resetAutoPlay(); });
  }

  // Touch Swipe Events
  track.addEventListener('touchstart', (e) => {
    isDragging = true;
    startX = e.touches[0].clientX;
    track.style.transition = 'none'; // remove transition for direct manipulation
    pauseAutoPlay();
  }, { passive: true });

  track.addEventListener('touchmove', (e) => {
    if (!isDragging) return;
    currentX = e.touches[0].clientX;
    const diff = currentX - startX;
    const slideWidth = slides[0].getBoundingClientRect().width;
    const baseTranslate = -(currentIndex * slideWidth);
    track.style.transform = `translateX(${baseTranslate + diff}px)`;
  }, { passive: true });

  track.addEventListener('touchend', (e) => {
    isDragging = false;
    track.style.transition = 'transform 0.5s cubic-bezier(0.25, 1, 0.5, 1)';
    const diff = currentX - startX;
    
    // Threshold for swipe
    if (Math.abs(diff) > 50) {
      if (diff > 0) prevSlide();
      else nextSlide();
    } else {
      updateCarousel(); // snap back
    }
    
    resetAutoPlay();
  });

  // Auto Play
  function startAutoPlay() {
    autoPlayInterval = setInterval(nextSlide, 5000);
  }
  function pauseAutoPlay() {
    clearInterval(autoPlayInterval);
  }
  function resetAutoPlay() {
    pauseAutoPlay();
    startAutoPlay();
  }

  // Hover to pause
  const carouselWrap = document.querySelector('.sb-trust-carousel-wrap');
  if (carouselWrap) {
    carouselWrap.addEventListener('mouseenter', pauseAutoPlay);
    carouselWrap.addEventListener('mouseleave', startAutoPlay);
  }

  // Handle Resize
  window.addEventListener('resize', () => {
    track.style.transition = 'none';
    updateCarousel();
    setTimeout(() => {
      track.style.transition = 'transform 0.5s cubic-bezier(0.25, 1, 0.5, 1)';
    }, 50);
  });

  startAutoPlay();
}
