// O conteúdo nasce no HTML. O JavaScript só troca estado depois.
(function () {
  "use strict";

  // Header transparente sobre o hero vira sólido depois de 80px de rolagem.
  var topo = document.querySelector("[data-topo].topo--sobre-hero");
  if (topo) {
    var marcar = function () {
      topo.classList.toggle("solido", window.scrollY > 80);
    };
    marcar();
    window.addEventListener("scroll", marcar, { passive: true });
  }

  // Régua de 140px abrindo quando a seção entra. É a única entrada animada.
  var alvos = document.querySelectorAll("[data-revelar]");
  if (alvos.length && "IntersectionObserver" in window) {
    var observador = new IntersectionObserver(function (entradas) {
      entradas.forEach(function (entrada) {
        if (entrada.isIntersecting) {
          entrada.target.classList.add("visivel");
          observador.unobserve(entrada.target);
        }
      });
    }, { threshold: 0.18 });
    alvos.forEach(function (alvo) { observador.observe(alvo); });
  }
})();
