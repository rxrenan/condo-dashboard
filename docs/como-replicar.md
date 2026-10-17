# Como replicar com dado real

A demo não usa dado real e não precisa de `.env`. Este arquivo é o caminho se um condomínio for piloto. O piloto em si é [A CONFIRMAR].

## 1. Não misture com este repositório público

Copie o projeto para um lugar privado. Não faça commit de ata, balancete, nota ou lista de moradores. O `.gitignore` já ignora `.env`.

## 2. De onde vêm os arquivos

O plano é exportar a ata em PDF e o balancete em CSV do aplicativo que o condomínio já usa.

- Existe API ou exportação estável? [A CONFIRMAR]
- Se não existir, o plano B é o conselho baixar o PDF da ata e o CSV (ou a planilha) do balancete e subir os dois arquivos. O formato exato do CSV real é [A CONFIRMAR]. A demo espera as colunas `data,documento,historico,categoria,fornecedor,valor`.

Não há conector pronto. Não coloque senha de morador nem de administradora em lugar nenhum.

## 3. Rode o modo determinístico

```bash
python demo.py --no-serve
```

Isso regrava `examples/saida/`. Leia `decisoes.json` e `despesas.json`. O layout fixo da demo não entende ata fora do padrão `DELIBERAÇÃO / Assunto / Trecho / Votação agregada / Resultado`. Ata escaneada como imagem precisa de OCR. O motor é [A CONFIRMAR].

## 4. Revisão humana

Edite `examples/revisao/decisoes.csv` e `examples/revisao/despesas.csv`. Só o estado `confirmada` entra na visão do morador. Confirmar uma despesa sem obra sugerida faz o pipeline parar, de propósito.

## 5. Modo opcional com modelo

Copie `.env.example` para `.env` e preencha `PAINEL_MODO=llm`, `PAINEL_LLM_BASE_URL`, `PAINEL_LLM_MODEL` e `PAINEL_LLM_API_KEY`. Os prompts estão em `prompts/`. O comando:

```bash
python demo.py --llm --no-serve
```

grava `examples/saida/llm-decisoes.bruto.txt` e não troca o painel publicado. O fornecedor do modelo é [A CONFIRMAR]. Sem as três variáveis, o comando para.

## 6. O que não subir

CPF, inadimplência, voto por unidade, nota com dado de funcionário, senha, boleto. Pagamento está fora do case.
