# 🧩 Aplicação de Método Heurístico para Decifração de Mensagens Utilizando Python

Este projeto implementa um **método heurístico de decifração automatizada** de mensagens codificadas em **binário ASCII**, inspirado em técnicas clássicas de análise de frequência e mapeamento posicional.  
A ferramenta foi desenvolvida em **Python** e estruturada como um **pipeline modular**, permitindo acompanhar cada etapa do processo de decifração — desde a leitura do arquivo binário até a geração do texto parcialmente traduzido.

---

## 🧠 Objetivo

O objetivo deste projeto é demonstrar como **técnicas heurísticas** e **análise de frequência de palavras** podem ser aplicadas para reconstruir textos cifrados de forma incremental.  
O método implementado identifica padrões linguísticos comuns na língua inglesa (como as palavras *A*, *I*, *IN*, *IS*, *THE*, *AND*, *FOR* etc.) e utiliza essas recorrências para inferir substituições de caracteres, refinando o texto a cada iteração.

---

## ⚙️ Estrutura do Projeto

```
📦 projeto-decifracao
├── decrypt.py                         # Script principal (orquestra o pipeline)
├── funcoes_decodificador.py           # Módulo com todas as funções do processo
├── top_words_banco_de_palavras.py     # Banco de palavras mais comuns em inglês
├── encoded_EXIST.txt                  # Arquivo de entrada (mensagem codificada em binário)
├── fluxograma.svg                     # Diagrama do pipeline de decifração
│
├── mensagens/                         # Saída intermediária (tokens e matrizes)
├── mapeamentos/                       # Arquivos com mapeamentos letra→letra
├── decifrados/                        # Arquivos decifrados parcialmente
├── palavrasUsadas/                    # Palavras aplicadas por subloop
│
└── README.md                          # Este arquivo
```

---

## 🧩 Funcionamento Geral

O pipeline de decifração segue as seguintes etapas principais:

1. **Leitura e Conversão:** Importa o arquivo binário e converte cada sequência de bits em caracteres ASCII.  
2. **Tokenização e Normalização:** Divide o texto em tokens e organiza-os por posição.  
3. **Ordenação:** Classifica tokens por comprimento e frequência.  
4. **Mapeamento Heurístico:**  
   - Identifica palavras de **1 letra** (A, I);  
   - Testa combinações de **2 letras** (AS, AT, IN, IS);  
   - Aplica fallback de **3 letras** (THE, AND, FOR, NOT).  
5. **Análise:** Calcula métricas de progresso (% de texto traduzido e % de palavras reconhecidas).  
6. **Geração do Texto Final:** Exporta o arquivo `encoded_decifrado.txt` com o melhor resultado.

O fluxograma abaixo (armazenado em `fluxograma.svg`) representa visualmente essas etapas.

---

## 🧰 Requisitos

- Python 3.8 ou superior  
- Bibliotecas padrão (nenhuma dependência externa)  
- Opcional: Inkscape (para converter o SVG em PDF caso use o artigo em LaTeX)

---

## 🚀 Como Executar

1. **Clone o repositório:**
   ```bash
   git clone https://github.com/<seu-usuario>/projeto-decifracao.git
   cd projeto-decifracao
   ```

2. **Adicione a mensagem binária:**
   - Coloque o arquivo codificado em `encoded_EXIST.txt`.

3. **Execute o pipeline:**
   ```bash
   python decrypt.py
   ```

4. **Confira os resultados:**
   - Arquivos intermediários: `mensagens/`, `mapeamentos/`, `decifrados/`  
   - Resultado final: `encoded_decifrado.txt`

---

## 📊 Métricas de Avaliação

O sistema apresenta duas métricas principais em cada execução:

- **Percentual de palavras reconhecidas:** relação entre palavras existentes no banco e total processado.  
- **Percentual de texto traduzido:** proporção de caracteres já substituídos por letras decifradas.

Essas métricas permitem comparar versões e acompanhar o avanço da decifração a cada iteração.

---

## 🧠 Referências Teóricas

- *O Jogo da Imitação* (2014) — Contexto histórico da decifração automatizada.  
- *O Escaravelho de Ouro* — Edgar Allan Poe (1843).  
- Peter Norvig — *English Letter Frequency Counts: Mayzner Revisited* (2012).  
- English Experts — *As palavras mais comuns da língua inglesa* (2010s).  
- L. Possani — *Criptografia: das origens à obra de Edgar Allan Poe* (YouTube, 2025).

---

## 🖼️ Fluxograma do Pipeline

O diagrama abaixo resume o fluxo completo do processo de decifração.

![Fluxograma do Pipeline](fluxograma.svg)

---

## 👨‍💻 Autor

**Marco Mello**  
Programa de Pós-Graduação em Ciência da Computação — UFABC  
📧 marcomello.e@gmail.com

---

## 📄 Licença

Este projeto é distribuído sob a licença **MIT**.  
Sinta-se à vontade para estudar, modificar e expandir o código.
