import os
from gtts import gTTS
import subprocess
import re

texto_roteiro = (
    "Fala, galera, hoje vamos mergulhar fundo em uma partida da USL Championship que promete muita emoção. É Colorado Springs Switchbacks FC contra San Antonio FC. Separa o bloco de notas que a análise de hoje é densa. "
    "[ABA: gols] "
    "Vamos começar pelos gols. A probabilidade de gol no primeiro tempo bate a setenta e quatro por cento, o que já abre os olhos para um jogo que pode começar quente. Over um ponto cinco aparece com oitenta por cento de chance. [FOCO: Over 1.5] Começando pelo over um ponto cinco, a linha é muito sólida, o que indica que dificilmente o jogo vai terminar com menos de dois gols. A tendência é de movimentação desde cedo. [OFF] [FOCO: Over 2.5] Passando para o over dois ponto cinco, a confiança cai um pouco, mas ainda é majoritária, com cinquenta e oito por cento. O jogo tem potencial para três ou mais gols, mas não é garantia. [OFF] [FOCO: Over 3.5] Por outro lado, o over três ponto cinco já é mais arriscado, com quarenta e um por cento. [OFF] [FOCO: Over 4.5] Verificando o over quatro ponto cinco, a chance despenca para vinte e cinco por cento, mostrando que uma goleada histórica é improvável. [OFF] [FOCO: BTTS] Analisando o ambas marcam, temos sessenta e dois por cento de probabilidade, o que é um número muito forte para um mercado como esse. Os dois times têm ataque forte e defesa frágil, ingrediente perfeito para os dois balançarem as redes. [OFF] [FOCO: Vencer a Partida] Quanto ao vencedor da partida, o Colorado Springs leva vantagem nos estudos, com quarenta e dois por cento de chance de vencer em casa, contra vinte e oito do San Antonio. O empate aparece com trinta por cento. [OFF] [FOCO: Chance Dupla] Destacando a chance dupla, o palpite principal é um x, ou seja, Colorado Springs não perde, com impressionantes setenta e dois por cento de confiança. [OFF] [FOCO: HT] Finalizando com o gol no primeiro tempo, a probabilidade de setenta e quatro por cento é um alerta claro: não durma no primeiro tempo, o jogo pode ser decidido antes do intervalo. [OFF] "
    "[ABA: escanteios] "
    "Agora vamos para os escanteios. A média de cantos combinada é altíssima, quase dezoito por partida. Isso é um prato cheio para quem gosta do mercado de cantos. [FOCO: Over 7.5] Olhando o over sete ponto cinco, a chance é de sessenta e sete por cento, um número muito confiável. [OFF] [FOCO: Over 8.5] Seguindo para o over oito ponto cinco, a confiança continua alta, com cinquenta e sete por cento. [OFF] [FOCO: Base do Jogo] A base do jogo, que é a média total de cantos, está em dezessete vírgula sete, um número absurdo que justifica explorar esse mercado. [OFF] [FOCO: Melhor Palpite] O melhor palpite, segundo nossa análise, é o total de cantos acima de seis vírgula cinco, uma linha mais segura. [OFF] [FOCO: Mais Escanteios] Por fim, analisando quem terá mais escanteios, o Colorado Springs leva vantagem com cinquenta e cinco por cento de probabilidade, contra trinta por cento do San Antonio. [OFF] "
    "[ABA: cartoes] "
    "Fechamos a análise com os cartões. A disciplina promete ser um ponto quente. A média de cartões por partida é zero, mas isso é um engano estatístico, pois os times costumam acumular muitas advertências. O over três ponto cinco cartões aparece com setenta e oito por cento de chance. [FOCO: Over 3.5] Começando pelo over três ponto cinco, a chance é altíssima, indicando um jogo pegado. [OFF] [FOCO: Over 4.5] Avançando para o over quatro ponto cinco, a confiança ainda é majoritária, com sessenta e dois por cento. [OFF] [FOCO: Over 5.5] Indo para o over cinco ponto cinco, a probabilidade cai para quarenta e oito por cento, mas ainda é um mercado viável. [OFF] [FOCO: Mais Cartões] E para fechar, o mais cartões: o San Antonio FC é o grande favorito para levar mais advertências, com sessenta e três por cento de chance, contra apenas dezenove do Colorado. Fica o alerta para a zaga visitante. [OFF]"
)

# Locução limpa (removendo as tags)
texto_locucao = re.sub(r'\[.*?\]', '', texto_roteiro).replace('  ', ' ').strip()

# Salvar o Roteiro
caminho_roteiro = "I:\\ROTEIRO VIDEOS\\AMERICA MG\\roteiro video\\roteiro_teste_gols.txt"
with open(caminho_roteiro, "w", encoding="utf-8") as f:
    f.write(texto_roteiro)
print(f"Roteiro salvo em: {caminho_roteiro}")

# Gerar Áudio
caminho_audio = "I:\\ROTEIRO VIDEOS\\AMERICA MG\\roteiro video\\audio_teste_gols.mp3"
print("Gerando áudio TTS...")
tts = gTTS(text=texto_locucao, lang='pt')
tts.save(caminho_audio)
print(f"Áudio salvo em: {caminho_audio}")

# Disparar gerar_video.py para Colorado Springs
url = "http://127.0.0.1:8000/pt-br/match/509302/colorado-springs-switchbacks-fc-vs-san-antonio-fc/"
comando = [
    ".\\venv\\Scripts\\python.exe",
    "video_maker/gerar_video.py",
    "--url", url,
    "--audio", caminho_audio,
    "--roteiro", caminho_roteiro
]

print("Iniciando gravação do Roteiro Completo (Gols + Escanteios + Cartões)...")
subprocess.run(comando)
print("Teste finalizado!")
