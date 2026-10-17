# Privacidade

Este repositório não tem dado real de morador. O texto abaixo é o desenho para um piloto, que ainda não existe.

## Papéis

Num piloto, o controlador tende a ser o condomínio, e a camada que lê ata e balancete tende a ser operadora. Contrato, base legal e registro das operações: [A CONFIRMAR]. Sem isso, não há piloto com documento real.

## O que não se publica

- CPF e documento de identidade. O código troca o padrão por `[documento mascarado]` antes de gravar a saída.
- Voto de cada unidade. Só o total (a favor, contra, abstenção).
- Quem registrou uma ocorrência de área comum. O JSON de ocorrência não tem esse campo. Se alguém colocar, o pipeline recusa.
- Lista de inadimplentes e nome em nota fiscal. A demo não traz esses dados. Num arquivo real, mascarar antes de indexar.
- A pergunta recusa quando pedem inadimplência, CPF ou voto de unidade, mesmo que o texto existisse na ata.

## O que a demo ainda não faz

Não há login. A visão do conselho é um botão, e o navegador recebe os itens em revisão para esse botão funcionar. Num piloto, essa visão exigiria acesso do conselho, separado do morador. Não copiar o padrão da demo para dado real.

A ata crua em `examples/atas/` guarda a linha de voto de unidade, para o teste mostrar que a saída a remove. Documento real não deve ser commitado. Ver `docs/como-replicar.md`.

## LGPD, em uma frase

Ata, ocorrência e nota podem ter nome, unidade e dado de terceiro. Publicar isso para todo o condomínio precisa de base legal, minimização e um responsável. Isso está em aberto: [A CONFIRMAR].
