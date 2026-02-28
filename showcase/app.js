const nodes = [...document.querySelectorAll(".reveal")];

const observer = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      entry.target.classList.add("visible");
      observer.unobserve(entry.target);
    });
  },
  { threshold: 0.15 }
);

nodes.forEach((node, index) => {
  node.style.transitionDelay = `${index * 70}ms`;
  observer.observe(node);
});
