// O conteúdo nasce no HTML e funciona sem JavaScript. Este arquivo só melhora:
// fecha o balão de ajuda e os menus (Esc, clique fora, botão "Entendi") e
// impede o balão de vazar pela direita da tela no computador.
(function () {
  "use strict";

  // Na página pública, o topo transparente sobre o hero fica sólido depois de 80px de rolagem.
  var topo = document.querySelector(".topo--sobre-hero");
  if (topo) {
    var marcar = function () { topo.classList.toggle("solido", window.scrollY > 80); };
    marcar();
    window.addEventListener("scroll", marcar, { passive: true });
  }

  var ajudas = Array.prototype.slice.call(document.querySelectorAll("details[data-ajuda]"));
  var menus = Array.prototype.slice.call(document.querySelectorAll("details[data-fecha-fora]"));
  var todos = ajudas.concat(menus);

  function ajustar(detalhe) {
    var balao = detalhe.querySelector(".ajuda__balao");
    if (!balao) return;
    balao.style.left = "";
    if (!window.matchMedia("(min-width: 800px)").matches) return;
    // Mede a partir do próprio <details>, que tem posição mesmo com o balão ainda
    // fechado. Medir o balão só funciona depois do evento `toggle`, que o navegador
    // dispara de forma assíncrona: quem abre e olha na mesma hora vê o balão vazado.
    var largura = balao.offsetWidth || 320;   // 320px é a largura do balão no CSS
    var direita = detalhe.getBoundingClientRect().left - 8 + largura;
    var sobra = direita - (document.documentElement.clientWidth - 12);
    if (sobra > 0) balao.style.left = (-8 - sobra) + "px";
  }

  ajudas.forEach(function (detalhe) {
    // No clique, antes do `toggle`: assim o balão já nasce dentro da tela.
    var gatilho = detalhe.querySelector("summary");
    if (gatilho) gatilho.addEventListener("click", function () { ajustar(detalhe); });

    detalhe.addEventListener("toggle", function () {
      if (!detalhe.open) return;
      ajudas.forEach(function (outro) { if (outro !== detalhe) outro.open = false; });
      ajustar(detalhe);
    });
    var fechar = detalhe.querySelector(".ajuda__fechar");
    if (fechar) {
      fechar.addEventListener("click", function () {
        detalhe.open = false;
        detalhe.querySelector("summary").focus();
      });
    }
  });

  document.addEventListener("keydown", function (evento) {
    if (evento.key !== "Escape") return;
    var abertos = todos.filter(function (d) { return d.open; });
    abertos.forEach(function (d) { d.open = false; });
    if (abertos.length) abertos[0].querySelector("summary").focus();
  });

  document.addEventListener("click", function (evento) {
    todos.forEach(function (d) {
      if (d.open && !d.contains(evento.target)) d.open = false;
    });
  });
})();
