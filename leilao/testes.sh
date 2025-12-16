#!/bin/bash

API="http://localhost:30080"

echo "1. CRIANDO LEILÃO "

horario_termino=$(date -d "+5 minutes" --iso-8601=seconds)

criar_leilao=$(curl -s -X POST "$API/create-auction" \
  -H "Content-Type: application/json" \
  -d "{
    \"titulo\": \"Xbox 360\",
    \"descricao\": \"Xbox 360 com Kinect\",
    \"preco_inicial\": 1000,
    \"horario_termino\": \"$horario_termino\"
  }")


leilao_id="auction:1"

echo "Leilão criado: $leilao_id"
echo

sleep 1

echo "2. ENVIANDO LANCES SIMULTÂNEOS "

usuarios=("Ellen" "Thiago" "Gabriel" "Evan" "Gabriel" "Evan" "Gabriel" "Joao" "Natalina" "Gabriel")

valor=1100

for usuario in "${usuarios[@]}"; do
  (
    curl -s -X POST "$API/place-bid" \
      -H "Content-Type: application/json" \
      -d "{
        \"leilao_id\": \"$leilao_id\",
        \"usuario\": \"$usuario\",
        \"email\": \"gabrielsa@estudante.ufscar.br\",
        \"valor\": $valor
      }" > /dev/null
  ) &
  
  valor=$((valor + 100))
done

wait

echo "Lances enviados"
echo

sleep 1

echo "3. DETALHES FINAIS DO LEILÃO "

curl -s "$API/auction/$leilao_id"

echo
echo "4. FIM DO TESTE "
