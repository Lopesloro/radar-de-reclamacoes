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

  // Área da equipe, tela Fontes: escolher o arquivo em vez de abrir, copiar e colar.
  // O texto vai para o campo de colar, e o envio continua o formulário comum.
  var importacao = document.querySelector("form[data-importacao]");
  if (importacao) {
    var escolha = importacao.querySelector("[data-escolher-arquivo]");
    var area = importacao.querySelector("textarea[name=conteudo_do_arquivo]");
    var recado = importacao.querySelector("[data-arquivo-recado]");
    var botao = importacao.querySelector("button[type=submit]");
    var rotulo = botao.textContent;

    if (escolha && window.FileReader) {
      var seletor = escolha.querySelector("input[type=file]");
      escolha.hidden = false;
      seletor.addEventListener("change", function () {
        var arquivo = seletor.files && seletor.files[0];
        if (!arquivo) return;
        var leitor = new FileReader();
        leitor.onload = function () {
          area.value = String(leitor.result).replace(/^﻿/, "");
          recado.textContent = "Arquivo " + arquivo.name + " carregado. Confira o negócio e clique em " + rotulo + ".";
        };
        leitor.onerror = function () {
          recado.textContent = "Não deu para ler esse arquivo. Cole o conteúdo no campo abaixo.";
        };
        leitor.readAsText(arquivo, "utf-8");
      });
    }

    // A importação leva de segundos a um minuto. Sem isto o botão parece morto, a
    // pessoa clica de novo e o mesmo arquivo entra em dois pedidos ao mesmo tempo.
    importacao.addEventListener("submit", function () {
      botao.disabled = true;
      botao.textContent = "Importando, pode levar até um minuto…";
    });
    // Voltar pelo navegador devolve a página guardada, com o botão ainda travado.
    window.addEventListener("pageshow", function () {
      botao.disabled = false;
      botao.textContent = rotulo;
    });
  }
})();
