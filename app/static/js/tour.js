// Tour de cinco passos no Resumo. Começa pelo botão "Primeira vez aqui?" ou por
// /resumo?tour=1 (link da página de Ajuda). Lembra que a pessoa já viu, se o
// navegador deixar guardar; se não deixar, tudo funciona do mesmo jeito.
(function () {
  "use strict";

  var CHAVE = "radar.tour.visto";
  var PASSOS = [
    { alvo: '[data-tour="1"]', texto: "Aqui estão os números do mês: quantas avaliações o sistema leu e quantas viraram reclamação. O ? explica cada número." },
    { alvo: '[data-tour="2"]', texto: "Cada negócio tem um sinal: Vai piorar, Fique de olho ou Tudo normal." },
    { alvo: '[data-tour="3"]', texto: "Esta frase resume o que deve acontecer com o assunto que mais cresce." },
    { alvo: '[data-tour="4"]', texto: "Por quê? mostra as possíveis causas, da mais provável para a menos provável." },
    { alvo: '[data-tour="5"], .menu-movel__botao', texto: "Em Ajuda está o significado de cada palavra e as perguntas mais comuns." }
  ];

  var iniciar = document.querySelector("[data-tour-iniciar]");
  if (!iniciar) return;

  function jaViu() {
    try { return window.localStorage.getItem(CHAVE) === "1"; } catch (erro) { return false; }
  }
  function marcarVisto() {
    try { window.localStorage.setItem(CHAVE, "1"); } catch (erro) { /* sem armazenamento: segue igual */ }
  }
  if (jaViu()) iniciar.textContent = "Ver o tour de novo";

  var caixa = null;
  var atual = -1;
  var destacado = null;

  function visivel(elemento) {
    return elemento.getClientRects().length > 0;
  }

  function alvoDo(passo) {
    var candidatos = Array.prototype.slice.call(document.querySelectorAll(passo.alvo));
    return candidatos.filter(visivel)[0] || null;
  }

  function montar() {
    caixa = document.createElement("div");
    caixa.className = "tour";
    caixa.setAttribute("role", "dialog");
    caixa.setAttribute("aria-label", "Tour do resumo");
    var passo = document.createElement("p");
    passo.className = "tour__passo";
    var texto = document.createElement("p");
    texto.className = "tour__texto";
    texto.setAttribute("aria-live", "polite");
    var botoes = document.createElement("div");
    botoes.className = "tour__botoes";
    var seguir = document.createElement("button");
    seguir.type = "button";
    seguir.className = "tour__seguir";
    var sair = document.createElement("button");
    sair.type = "button";
    sair.className = "tour__sair";
    sair.textContent = "Sair do tour";
    botoes.appendChild(seguir);
    botoes.appendChild(sair);
    caixa.appendChild(passo);
    caixa.appendChild(texto);
    caixa.appendChild(botoes);
    seguir.addEventListener("click", function () { mostrar(atual + 1); });
    sair.addEventListener("click", terminar);
    document.body.appendChild(caixa);
  }

  function mostrar(indice) {
    if (indice >= PASSOS.length) { terminar(); return; }
    atual = indice;
    if (destacado) destacado.classList.remove("tour-destaque");
    destacado = alvoDo(PASSOS[indice]);
    if (destacado) {
      destacado.classList.add("tour-destaque");
      destacado.scrollIntoView({ block: "center" });
    }
    caixa.querySelector(".tour__passo").textContent = "Passo " + (indice + 1) + " de " + PASSOS.length;
    caixa.querySelector(".tour__texto").textContent = PASSOS[indice].texto;
    var seguir = caixa.querySelector(".tour__seguir");
    seguir.textContent = indice === PASSOS.length - 1 ? "Terminar" : "Próximo";
    seguir.focus();
  }

  function terminar() {
    if (destacado) destacado.classList.remove("tour-destaque");
    destacado = null;
    if (caixa) caixa.remove();
    caixa = null;
    marcarVisto();
    iniciar.textContent = "Ver o tour de novo";
    iniciar.focus();
  }

  function comecar() {
    if (!caixa) montar();
    mostrar(0);
  }

  iniciar.addEventListener("click", comecar);
  document.addEventListener("keydown", function (evento) {
    if (evento.key === "Escape" && caixa) terminar();
  });
  if (/[?&]tour=1\b/.test(window.location.search)) comecar();
})();
