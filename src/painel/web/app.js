const MESES = [
  "janeiro", "fevereiro", "março", "abril", "maio", "junho",
  "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
];

const NAV = [
  ["/", "Início"],
  ["/obras", "Obras"],
  ["/decisoes", "Decisões"],
  ["/ocorrencias", "Ocorrências"],
  ["/mudancas", "Mudanças"],
  ["/perguntas", "Perguntas"],
];

const ui = {
  visao: sessionStorage.getItem("painel-visao") || "morador",
  texto: "",
  resposta: null,
  pendente: false,
  erro: null,
};

let bruto = null;

function esc(valor) {
  return String(valor ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[char]));
}

function brl(centavos) {
  const sinal = centavos < 0 ? "-" : "";
  const valor = Math.abs(Number(centavos) || 0);
  const reais = Math.floor(valor / 100);
  const cents = String(valor % 100).padStart(2, "0");
  const inteiro = String(reais).replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  return `${sinal}R$ ${inteiro},${cents}`;
}

function dataLonga(iso) {
  if (!iso) return "sem data";
  const [ano, mes, dia] = iso.split("-");
  return `${Number(dia)} de ${MESES[Number(mes) - 1]} de ${ano}`;
}

function mesAno(competencia) {
  const [ano, mes] = competencia.split("-");
  return `${MESES[Number(mes) - 1]} de ${ano}`;
}

function dataCurta(iso) {
  if (!iso) return "sem data";
  const [ano, mes, dia] = iso.split("-");
  return `${dia}/${mes}/${ano}`;
}

function status(codigo, rotulo) {
  return `<span class="status status-${esc(codigo)}">${esc(rotulo)}</span>`;
}

function rota() {
  const hash = (location.hash || "#/").replace(/^#/, "");
  return hash.split("?")[0].split("/").filter(Boolean);
}

function atual() {
  if (!bruto) return null;
  if (ui.visao === "conselho") return bruto;
  return {
    ...bruto,
    meta: { ...bruto.meta, visao: "morador" },
    decisoes: bruto.decisoes.filter((item) => item.revisao === "confirmada"),
    obras: bruto.obras.map((obra) => ({ ...obra, sugestoes: [] })),
    sugestoes_despesas: [],
    revisar_despesas: [],
  };
}

function obraDa(id) {
  return (bruto?.obras || []).find((obra) => obra.decisao_id === id);
}

function percentual(obra) {
  if (!obra.orcamento_aprovado_centavos) return null;
  return Math.round((obra.realizado_centavos / obra.orcamento_aprovado_centavos) * 100);
}

function etapaTexto(obra) {
  if (obra.status === "nao_iniciada") return "Sem etapa iniciada";
  return `Etapa ${obra.etapa_atual} de ${obra.etapas_total}`;
}

function gastoTexto(obra) {
  if (obra.orcamento_aprovado_centavos == null) return "Sem valor aprovado";
  return `${obra.realizado_texto} de ${obra.orcamento_aprovado_texto}`;
}

function cadeia(obra) {
  const decisao = obra.decisao;
  return `
    <div class="cadeia">
      <article>
        <p class="kicker">1 · Decisão</p>
        <h3>${esc(decisao.assembleia)} · ${esc(dataLonga(decisao.data))}</h3>
        <blockquote class="trecho">${esc(decisao.trecho)}</blockquote>
        <p class="fonte">${esc(decisao.arquivo)}, página ${esc(decisao.pagina)}. Votação agregada: ${esc(decisao.votacao_texto)}</p>
      </article>
      <article>
        <p class="kicker">2 · Obra</p>
        <h3>${esc(obra.titulo)}</h3>
        <p>${status(obra.status, obra.status_rotulo)} ${esc(etapaTexto(obra))}</p>
        <p class="fonte">Responsável: ${esc(obra.responsavel)}</p>
      </article>
      <article>
        <p class="kicker">3 · Gasto</p>
        <h3>${esc(gastoTexto(obra))}</h3>
        ${barra(obra)}
        <p class="fonte">${obra.gastos.length === 1 ? "1 lançamento confirmado" : `${obra.gastos.length} lançamentos confirmados`}${obra.sugestoes_ocultas ? `. ${obra.sugestoes_ocultas} em revisão, fora da soma.` : ""}</p>
      </article>
    </div>
  `;
}

function barra(obra) {
  const pct = percentual(obra);
  if (pct == null) return `<p class="fonte">A ata não aprovou valor.</p>`;
  const largura = Math.max(0, Math.min(100, pct));
  return `
    <div class="trilho" aria-hidden="true"><span style="width:${largura}%"></span></div>
    <p class="fonte">${pct}% do valor aprovado, só com lançamento confirmado.</p>
  `;
}

function mini(obra) {
  return `
    <ol class="mini">
      <li><span>Decisão</span>${esc(obra.decisao.assembleia)} ${esc(dataCurta(obra.decisao.data))}</li>
      <li><span>Obra</span>${esc(etapaTexto(obra))}</li>
      <li><span>Gasto</span>${esc(gastoTexto(obra))}</li>
    </ol>
  `;
}

function cardObra(obra) {
  return `
    <a class="card" href="#/obras/${esc(obra.id)}">
      <div class="card-topo">
        <h3>${esc(obra.titulo)}</h3>
        ${status(obra.status, obra.status_rotulo)}
      </div>
      <p class="mudo">${esc(obra.responsavel)}</p>
      ${mini(obra)}
    </a>
  `;
}

function rodape(painel) {
  return `<p class="rodape">${esc(painel.meta.aviso)} Sem pagamento nesta tela. A cor marca só o status.</p>`;
}

function faixa(painel) {
  if (painel.meta.visao !== "conselho") return "";
  return `<p class="faixa">Visão do conselho. Sugestão e item sem revisão não aparecem para o morador. Nesta demo não há login: num piloto, esta visão exigiria acesso do conselho. Confirmar aqui vale só nesta sessão.</p>`;
}

function viewInicio(painel) {
  const ativas = painel.obras.filter((obra) => obra.status === "em_andamento");
  const outras = painel.obras.filter((obra) => obra.status !== "em_andamento");
  const decisoes = [...painel.decisoes].sort((a, b) => b.data.localeCompare(a.data)).slice(0, 4);
  const abertas = painel.ocorrencias.filter((item) => item.status !== "concluida");
  const mes = painel.meta.competencia_resumo;
  const mudancas = painel.mudancas.filter((item) => item.data.startsWith(mes));
  return `
    ${faixa(painel)}
    <p class="kicker">Visão geral</p>
    <h1>O que está acontecendo</h1>
    <p class="dek">A gestão mostra, numa linha só, a decisão da assembleia, a obra e o gasto confirmado.</p>
    <article class="resumo">
      <p class="kicker">Resumo de ${esc(mesAno(mes))}</p>
      <p>${esc(painel.resumo.texto)}</p>
      <p class="fonte">Fontes: ${esc(painel.resumo.fontes.map((fonte) => fonte.arquivo).join(", "))}. Modo determinístico, sem modelo de linguagem.</p>
    </article>
    <section class="secao">
      <h2>Obras em andamento</h2>
      <div class="grade">${ativas.map(cardObra).join("") || `<p class="vazio">Nenhuma obra em andamento.</p>`}</div>
    </section>
    <section class="secao">
      <h2>Outras obras</h2>
      <div class="grade">${outras.map(cardObra).join("")}</div>
    </section>
    <div class="duas">
      <section class="secao">
        <h2>Decisões recentes</h2>
        <div class="lista">${decisoes.map((item) => `
          <a class="item" href="#/decisoes">
            <time>${esc(dataCurta(item.data))}</time>
            <span>${esc(item.assunto)}</span>
            ${status(item.execucao, item.execucao_rotulo)}
          </a>`).join("")}</div>
      </section>
      <section class="secao">
        <h2>Ocorrências de área comum</h2>
        <div class="lista">${abertas.map((item) => `
          <a class="item" href="#/ocorrencias">
            <time>${esc(dataCurta(item.aberta_em))}</time>
            <span>${esc(item.titulo)}</span>
            ${status(item.status, item.status_rotulo)}
          </a>`).join("") || `<p class="vazio">Nenhuma ocorrência aberta.</p>`}</div>
      </section>
    </div>
    <section class="secao">
      <h2>Mudanças do mês</h2>
      <div class="lista">${mudancas.map((item) => `
        <a class="item" href="#/mudancas">
          <time>${esc(dataCurta(item.data))}</time>
          <span>${esc(item.titulo)}: ${esc(item.depois)}</span>
        </a>`).join("") || `<p class="vazio">Nenhuma mudança neste mês.</p>`}</div>
    </section>
    ${rodape(painel)}
  `;
}

function viewObras(painel) {
  const obras = [...painel.obras].sort((a, b) => a.titulo.localeCompare(b.titulo, "pt"));
  return `
    ${faixa(painel)}
    <p class="kicker">Obras</p>
    <h1>Da decisão ao gasto</h1>
    <p class="dek">Cada obra publicada nasce de um trecho da ata e só soma o lançamento que o conselho confirmou.</p>
    <div class="lista">${obras.map((obra) => `
      <section class="secao">
        <div class="linha">
          <h2>${esc(obra.titulo)}</h2>
          ${status(obra.status, obra.status_rotulo)}
        </div>
        ${cadeia(obra)}
        <p><a href="#/obras/${esc(obra.id)}">Abrir cronograma, fotos e lançamentos</a></p>
      </section>`).join("")}</div>
    ${painel.meta.visao === "conselho" ? blocoRevisar(painel) : ""}
    ${rodape(painel)}
  `;
}

function blocoRevisar(painel) {
  if (!painel.revisar_despesas.length) return "";
  return `
    <section class="secao">
      <h2>Lançamentos sem obra</h2>
      <p class="mudo">A categoria fala de reforma, mas nenhum termo indica o projeto. A demo não inventa o vínculo.</p>
      ${tabela(painel.revisar_despesas, false)}
    </section>
  `;
}

function tabela(linhas, confirmar) {
  return `
    <table>
      <thead>
        <tr>
          <th>Data</th><th>Documento</th><th>Histórico</th><th>Fornecedor</th>
          <th class="num">Valor</th>${confirmar ? "<th></th>" : ""}
        </tr>
      </thead>
      <tbody>
        ${linhas.map((linha) => `
          <tr>
            <td>${esc(dataCurta(linha.data))}</td>
            <td>${esc(linha.documento)}<div class="fonte">${esc(linha.arquivo)}, linha ${esc(linha.linha)}</div></td>
            <td>${esc(linha.historico)}<div class="fonte">${esc(linha.motivo || "")}</div></td>
            <td>${esc(linha.fornecedor)}</td>
            <td class="num">${esc(brl(linha.valor_centavos))}</td>
            ${confirmar ? `<td><button type="button" data-confirmar="${esc(linha.documento)}">Confirmar vínculo</button></td>` : ""}
          </tr>`).join("")}
      </tbody>
    </table>
  `;
}

function viewObra(painel, id) {
  const obra = painel.obras.find((item) => item.id === id) || bruto.obras.find((item) => item.id === id);
  if (!obra) {
    return `<h1>Obra não encontrada</h1><p><a href="#/obras">Voltar às obras</a></p>`;
  }
  const visivel = painel.meta.visao === "conselho" ? bruto.obras.find((item) => item.id === id) : obra;
  return `
    ${faixa(painel)}
    <p class="kicker"><a href="#/obras">Obras</a></p>
    <div class="linha">
      <h1>${esc(visivel.titulo)}</h1>
      ${status(visivel.status, visivel.status_rotulo)}
    </div>
    <p class="dek">${esc(visivel.nota || "")}</p>
    ${cadeia(visivel)}
    <div class="duas" style="margin-top:18px">
      <section class="card">
        <h2>Cronograma</h2>
        <ol class="etapas">
          ${visivel.etapas.map((etapa) => `
            <li class="marca-${esc(etapa.estado)}">
              <div>
                <strong>${esc(etapa.n)}. ${esc(etapa.titulo)}</strong>
                <div>${status(etapa.estado, etapa.estado === "concluida" ? "Concluída" : etapa.estado === "em_andamento" ? "Em andamento" : etapa.estado === "pausada" ? "Pausada" : "Não iniciada")}</div>
                <p class="fonte">${etapa.inicio ? esc(dataCurta(etapa.inicio)) : "sem início"}${etapa.fim ? " a " + esc(dataCurta(etapa.fim)) : ""}</p>
              </div>
            </li>`).join("")}
        </ol>
      </section>
      <section class="card">
        <h2>Fotos</h2>
        ${visivel.fotos.length ? `<div class="fotos">${visivel.fotos.map((foto) => `
          <figure class="foto">
            <img src="${esc(foto.src)}" alt="${esc(foto.legenda)}">
            <figcaption>${esc(foto.legenda)}</figcaption>
          </figure>`).join("")}</div>` : `<p class="vazio">Sem fotos. A obra não começou.</p>`}
      </section>
    </div>
    <section class="secao">
      <h2>Gastos confirmados</h2>
      ${visivel.gastos.length ? tabela(visivel.gastos, false) : `<p class="vazio">Nenhum lançamento confirmado.</p>`}
    </section>
    ${painel.meta.visao === "conselho" && visivel.sugestoes.length ? `
      <section class="secao">
        <h2>Sugestões aguardando o conselho</h2>
        <p class="mudo">Estes valores não entram no realizado até a confirmação.</p>
        ${tabela(visivel.sugestoes, true)}
      </section>` : ""}
    ${rodape(painel)}
  `;
}

function viewDecisoes(painel) {
  const grupos = new Map();
  const ordenadas = [...painel.decisoes].sort((a, b) => b.data.localeCompare(a.data) || a.numero - b.numero);
  for (const item of ordenadas) {
    const chave = `${item.data}|${item.assembleia_titulo}`;
    if (!grupos.has(chave)) grupos.set(chave, []);
    grupos.get(chave).push(item);
  }
  const blocos = [...grupos.entries()].map(([chave, itens]) => {
    const [data, titulo] = chave.split("|");
    return `
      <section class="grupo">
        <p class="kicker">${esc(itens[0].assembleia)} · ${esc(itens[0].arquivo)}</p>
        <h2>${esc(titulo)}</h2>
        <p class="mudo">${esc(dataLonga(data))}. O voto de cada unidade não aparece.</p>
        ${itens.map((item) => {
          const obra = obraDa(item.id);
          return `
            <article class="card" style="margin-top:12px">
              <div class="linha">
                <h3>${esc(item.numero)}. ${esc(item.assunto)}</h3>
                <span>${status(item.resultado, item.resultado_rotulo)} ${status(item.execucao, item.execucao_rotulo)}</span>
              </div>
              <blockquote class="trecho">${esc(item.trecho)}</blockquote>
              <p class="fonte">Página ${esc(item.pagina)}. Votação agregada: ${esc(item.votacao_texto)}</p>
              ${obra && item.revisao === "confirmada" ? `<p><a href="#/obras/${esc(obra.id)}">Ver a obra</a></p>` : ""}
            </article>`;
        }).join("")}
      </section>`;
  }).join("");
  return `
    ${faixa(painel)}
    <p class="kicker">Decisões</p>
    <h1>O que a assembleia decidiu</h1>
    <p class="dek">Cada item sai da ata com página e trecho. Sem a revisão do conselho, o morador não vê.</p>
    <div class="linha-tempo">${blocos}</div>
    ${rodape(painel)}
  `;
}

function viewOcorrencias(painel) {
  const itens = [...painel.ocorrencias].sort((a, b) => b.aberta_em.localeCompare(a.aberta_em));
  return `
    ${faixa(painel)}
    <p class="kicker">Ocorrências</p>
    <h1>Problemas de área comum</h1>
    <p class="dek">O status é público. O nome de quem registrou não aparece.</p>
    <div class="lista">${itens.map((item) => `
      <article class="card">
        <div class="linha">
          <h2>${esc(item.titulo)}</h2>
          ${status(item.status, item.status_rotulo)}
        </div>
        <p class="mudo">${esc(item.area)} · aberta em ${esc(dataLonga(item.aberta_em))}${item.concluida_em ? " · concluída em " + esc(dataLonga(item.concluida_em)) : ""}</p>
        <p>${esc(item.descricao)}</p>
        <p class="fonte">${esc(item.atualizacao)}</p>
      </article>`).join("")}</div>
    ${rodape(painel)}
  `;
}

function viewMudancas(painel) {
  const itens = [...painel.mudancas].sort((a, b) => b.data.localeCompare(a.data));
  return `
    ${faixa(painel)}
    <p class="kicker">Mudanças</p>
    <h1>O que mudou na rotina</h1>
    <p class="dek">Regra, horário e fornecedor, com o antes, o depois e a fonte.</p>
    <div class="lista">${itens.map((item) => `
      <article class="card">
        <div class="linha">
          <h2>${esc(item.titulo)}</h2>
          <time>${esc(dataLonga(item.data))}</time>
        </div>
        <div class="antes-depois">
          <div><span>Antes</span>${esc(item.antes)}</div>
          <div><span>Depois</span>${esc(item.depois)}</div>
        </div>
        <p class="fonte">${esc(item.fonte)}</p>
      </article>`).join("")}</div>
    ${rodape(painel)}
  `;
}

function viewPerguntas(painel) {
  const resposta = ui.resposta;
  return `
    ${faixa(painel)}
    <p class="kicker">Perguntas</p>
    <h1>Pergunte ao condomínio</h1>
    <p class="dek">A resposta cita a ata, o balancete ou o registro publicado. Se não houver fonte, o painel recusa. Não interpreta norma.</p>
    <form id="form-pergunta" class="form-pergunta">
      <label class="somente-leitor" for="campo-pergunta">Pergunta</label>
      <input id="campo-pergunta" name="pergunta" value="${esc(ui.texto)}" placeholder="Ex.: qual o valor aprovado da pintura da garagem?" autocomplete="off">
      <button type="submit" ${ui.pendente ? "disabled" : ""}>${ui.pendente ? "Buscando" : "Perguntar"}</button>
    </form>
    <div class="chips">
      ${painel.perguntas_exemplo.map((texto) => `<button type="button" data-pergunta="${esc(texto)}">${esc(texto)}</button>`).join("")}
    </div>
    <div id="resposta">
      ${ui.pendente ? `<p class="mudo">Procurando nos documentos publicados.</p>` : ""}
      ${resposta ? `
        <article class="resposta">
          <p>${esc(resposta.resposta)}</p>
          ${resposta.citacoes.length ? resposta.citacoes.map((citacao) => `
            <div class="citacao">
              <p class="fonte">${esc(citacao.rotulo)}</p>
              <blockquote class="trecho">${esc(citacao.trecho)}</blockquote>
            </div>`).join("") : `<p class="fonte">${resposta.recusa ? "Sem citação, porque não há fonte publicada para esta pergunta." : ""}</p>`}
        </article>` : ""}
    </div>
    ${rodape(painel)}
  `;
}

function desenharMenu(painel) {
  const partes = rota();
  const atualRota = partes[0] || "";
  document.getElementById("menu").innerHTML = `
    <p class="marca">Painel<span>do condomínio</span></p>
    <nav class="nav" aria-label="Seções">
      ${NAV.map(([href, rotulo]) => {
        const chave = href === "/" ? "" : href.slice(1);
        const corrente = chave === atualRota;
        return `<a href="#${href}" ${corrente ? 'aria-current="page"' : ""}>${esc(rotulo)}</a>`;
      }).join("")}
    </nav>
    <p class="lado-rodape"><strong>${esc(painel.meta.condominio)}</strong>Dados fictícios</p>
  `;
}

function desenharTopo(painel) {
  const escuro = document.documentElement.getAttribute("data-theme") === "dark";
  document.getElementById("topo").innerHTML = `
    <div>
      <p class="kicker">${esc(painel.meta.condominio)}</p>
      <p class="atualizado">Atualizado em ${esc(dataLonga(painel.meta.atualizado_em))} · dados fictícios</p>
    </div>
    <div class="acoes">
      <div class="seg" role="group" aria-label="Visão">
        <button type="button" data-visao="morador" aria-pressed="${ui.visao === "morador"}">Morador</button>
        <button type="button" data-visao="conselho" aria-pressed="${ui.visao === "conselho"}">Conselho</button>
      </div>
      <button type="button" data-acao="tema">${escuro ? "Tema claro" : "Tema escuro"}</button>
    </div>
  `;
}

function render() {
  const painel = atual();
  if (!painel) return;
  desenharMenu(painel);
  desenharTopo(painel);
  const partes = rota();
  const conteudo = document.getElementById("conteudo");
  let html = "";
  if (!partes.length) html = viewInicio(painel);
  else if (partes[0] === "obras" && partes[1]) html = viewObra(painel, partes[1]);
  else if (partes[0] === "obras") html = viewObras(painel);
  else if (partes[0] === "decisoes") html = viewDecisoes(painel);
  else if (partes[0] === "ocorrencias") html = viewOcorrencias(painel);
  else if (partes[0] === "mudancas") html = viewMudancas(painel);
  else if (partes[0] === "perguntas") html = viewPerguntas(painel);
  else html = `<h1>Página não encontrada</h1><p><a href="#/">Voltar ao início</a></p>`;
  conteudo.innerHTML = html;
}

function confirmar(documento) {
  for (const obra of bruto.obras) {
    const indice = obra.sugestoes.findIndex((item) => item.documento === documento);
    if (indice < 0) continue;
    const item = obra.sugestoes.splice(indice, 1)[0];
    item.revisao = "confirmada";
    item.publicada = true;
    item.revisar = false;
    obra.gastos.push(item);
    obra.gastos.sort((a, b) => a.data.localeCompare(b.data) || a.documento.localeCompare(b.documento));
    obra.realizado_centavos += item.valor_centavos;
    obra.realizado_texto = brl(obra.realizado_centavos);
    obra.sugestoes_ocultas = obra.sugestoes.length;
  }
  bruto.sugestoes_despesas = bruto.sugestoes_despesas.filter((item) => item.documento !== documento);
  render();
}

async function fazerPergunta(texto) {
  ui.texto = texto;
  ui.pendente = true;
  ui.resposta = null;
  render();
  const campo = document.getElementById("campo-pergunta");
  if (campo) campo.focus();
  try {
    const resposta = await fetch("/api/perguntas", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pergunta: texto }),
    });
    ui.resposta = await resposta.json();
  } catch (erro) {
    ui.resposta = {
      recusa: true,
      motivo: "rede",
      resposta: "Não foi possível consultar os documentos agora.",
      citacoes: [],
    };
  }
  ui.pendente = false;
  render();
  const caixa = document.getElementById("resposta");
  if (caixa) caixa.scrollIntoView({ block: "nearest" });
}

document.body.addEventListener("click", (evento) => {
  const tema = evento.target.closest("[data-acao='tema']");
  if (tema) {
    const proximo = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", proximo);
    localStorage.setItem("painel-tema", proximo);
    render();
    return;
  }
  const visao = evento.target.closest("[data-visao]");
  if (visao) {
    ui.visao = visao.dataset.visao;
    sessionStorage.setItem("painel-visao", ui.visao);
    render();
    return;
  }
  const confirmarBtn = evento.target.closest("[data-confirmar]");
  if (confirmarBtn) {
    confirmar(confirmarBtn.dataset.confirmar);
    return;
  }
  const pergunta = evento.target.closest("[data-pergunta]");
  if (pergunta) {
    if (location.hash !== "#/perguntas") location.hash = "#/perguntas";
    fazerPergunta(pergunta.dataset.pergunta);
  }
});

document.body.addEventListener("submit", (evento) => {
  if (evento.target.id !== "form-pergunta") return;
  evento.preventDefault();
  fazerPergunta(new FormData(evento.target).get("pergunta") || "");
});

window.addEventListener("hashchange", render);

async function boot() {
  try {
    const resposta = await fetch("/api/painel?visao=conselho");
    if (!resposta.ok) throw new Error("painel indisponível");
    bruto = await resposta.json();
    render();
  } catch (erro) {
    document.getElementById("conteudo").innerHTML = `<h1>Não foi possível abrir a demo</h1><p class="mudo">Rode <code>python demo.py</code> e abra o endereço local.</p>`;
  }
}

boot();
