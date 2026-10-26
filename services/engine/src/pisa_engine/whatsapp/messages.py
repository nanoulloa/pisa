# Generated from apps/web/messages by `make gen`. Do not edit by hand.
# ruff: noqa: E501, RUF001
"""Copy for the WhatsApp bot: its own namespace plus verdicts, errors and explanations."""

import json
from typing import Any

MESSAGES: dict[str, dict[str, Any]] = json.loads(
    r"""
{
 "en": {
  "WhatsApp": {
   "welcome": "Hi, I'm Pisa. Forward me a video where something falls, is thrown or bounces, and I'll tell you whether real physics could have made it. I don't check faces, voices or lip sync.",
   "received": "Got it. I'm measuring how things move in it and will reply in under a minute. Pisa deletes your video within 24 hours and keeps only the measurements.",
   "onlyVideos": "I can only check videos. Forward me the video you want to check.",
   "tooLarge": "This video is larger than 16 MB. Send a shorter one, up to 60 seconds.",
   "rateLimited": "You've checked many videos in the last hour. Try again later.",
   "busy": "Pisa is getting a lot of videos right now. Try again in a while.",
   "frequentlyForwarded": "This video has been forwarded many times.",
   "details": "Measurements and evidence: {link}",
   "tryAnother": "You can try another video.",
   "legend": {
    "fit": "In the video, the lime circle follows the closest path real gravity allows.",
    "earth_gravity": "In the video, the lime circle shows where Earth's gravity would take it.",
    "partner": "In the video, each lime circle shows where the object would be if both fell together.",
    "elastic_bounce": "In the video, the lime circle shows the highest bounce real physics allows."
   }
  },
  "Verdict": {
   "physically_impossible": "Physically impossible",
   "consistent_with_real_physics": "Consistent with real physics",
   "inconclusive": "Inconclusive"
  },
  "Errors": {
   "unsupported_format": "This file isn't a video Pisa can read. Try an MP4 or MOV.",
   "video_too_long": "This video is longer than 60 seconds. Trim it to the moment that matters and try again.",
   "file_too_large": "This file is larger than 50 MB.",
   "unknown_duration": "Pisa couldn't tell how long this video is. Try exporting it again as MP4.",
   "resolution_too_high": "This video's resolution is too high. Try a version at 4K or less.",
   "transcode_failed": "Pisa couldn't prepare this video for measuring. Try exporting it again as MP4.",
   "empty_window": "There is nothing to measure in the part of the video that was selected.",
   "paid_calls_disabled": "Tracking is paused right now. Try again later.",
   "spend_cap_reached": "Pisa has reached its analysis limit for now. Try again later.",
   "network": "Pisa can't be reached. Check your connection and try again.",
   "job_not_found": "We couldn't find this check. It may have expired.",
   "internal_error": "Something went wrong on our side. Try again."
  },
  "Explanations": {
   "slows_down_while_falling": "The object slows down while it is still falling. Gravity and air can't do that.",
   "acceleration_grows": "The object speeds up faster and faster as it falls. Gravity pulls steadily, so real falls don't do that.",
   "accelerates_upward": "The object speeds up toward the sky, as if gravity pulled upward.",
   "impossible": "The way this object moves breaks a law of physics that every real fall follows.",
   "consistent": "The object speeds up at a steady rate as it falls, the way real gravity makes things fall.",
   "weak_violation": "Something in the motion looks off, but not clearly enough to call it impossible.",
   "no_measurable_acceleration": "The object moves at a steady speed, so there is no fall to measure.",
   "depth_change": "The object moves toward or away from the camera, which bends its path on screen too much to measure.",
   "too_few_samples": "The object is visible in too few frames to measure its motion.",
   "no_measurable_events": "Pisa couldn't find a fall, throw or bounce it could measure in this video.",
   "pair_falls_apart": "Two objects released together fall at different rates. Under real gravity they fall side by side, as Galileo showed.",
   "bounce_gains_energy": "The object leaves the bounce faster than it arrived. A real bounce always loses some energy.",
   "gravity_changes": "Gravity changes strength from one flight to the next. In a real video, even in slow motion, it stays the same.",
   "camera_motion": "The camera moves too much to measure the object against the background.",
   "gravity_too_weak": "The object falls as if gravity were weaker than on Earth. A slow-motion video looks exactly like this, so Pisa does not call it impossible.",
   "gravity_too_strong": "The object falls as if gravity were stronger than on Earth. A sped-up video looks like this, so Pisa does not call it impossible.",
   "no_free_flight": "Nothing in this video falls, flies or bounces on its own, so there is no motion Pisa can check.",
   "too_unclear": "Something falls, flies or bounces, but it is too small, blurred, hidden or brief to follow."
  }
 },
 "es": {
  "WhatsApp": {
   "welcome": "Hola, soy Pisa. Reenvíame un video en el que algo caiga, se lance o rebote y te digo si la física real pudo producirlo. No reviso rostros, voces ni sincronización de labios.",
   "received": "Recibido. Estoy midiendo cómo se mueve lo que aparece y te respondo en menos de un minuto. Pisa borra tu video en un máximo de 24 horas y solo guarda las mediciones.",
   "onlyVideos": "Solo puedo revisar videos. Reenvíame el video que quieres comprobar.",
   "tooLarge": "Este video pesa más de 16 MB. Envía uno más corto, de hasta 60 segundos.",
   "rateLimited": "Ya revisaste muchos videos en la última hora. Vuelve a intentarlo más tarde.",
   "busy": "Pisa está recibiendo muchos videos ahora mismo. Vuelve a intentarlo en un rato.",
   "frequentlyForwarded": "Este video se ha reenviado muchas veces.",
   "details": "Mediciones y evidencia: {link}",
   "tryAnother": "Puedes probar con otro video.",
   "legend": {
    "fit": "En el video, el círculo verde lima sigue el camino más cercano que permite la gravedad real.",
    "earth_gravity": "En el video, el círculo verde lima muestra adónde lo llevaría la gravedad de la Tierra.",
    "partner": "En el video, cada círculo verde lima muestra dónde estaría el objeto si los dos cayeran juntos.",
    "elastic_bounce": "En el video, el círculo verde lima muestra el rebote más alto que permite la física real."
   }
  },
  "Verdict": {
   "physically_impossible": "Físicamente imposible",
   "consistent_with_real_physics": "Consistente con la física real",
   "inconclusive": "No concluyente"
  },
  "Errors": {
   "unsupported_format": "Este archivo no es un video que Pisa pueda leer. Prueba con un MP4 o MOV.",
   "video_too_long": "Este video dura más de 60 segundos. Recórtalo al momento que importa y vuelve a intentarlo.",
   "file_too_large": "Este archivo pesa más de 50 MB.",
   "unknown_duration": "Pisa no pudo saber cuánto dura este video. Prueba a exportarlo de nuevo como MP4.",
   "resolution_too_high": "La resolución de este video es demasiado alta. Prueba con una versión de 4K o menos.",
   "transcode_failed": "Pisa no pudo preparar este video para medirlo. Prueba a exportarlo de nuevo como MP4.",
   "empty_window": "No hay nada que medir en la parte del video seleccionada.",
   "paid_calls_disabled": "El seguimiento está en pausa por ahora. Vuelve a intentarlo más tarde.",
   "spend_cap_reached": "Pisa alcanzó su límite de análisis por ahora. Vuelve a intentarlo más tarde.",
   "network": "No se puede conectar con Pisa. Revisa tu conexión y vuelve a intentarlo.",
   "job_not_found": "No encontramos esta revisión. Puede que haya caducado.",
   "internal_error": "Algo falló de nuestro lado. Vuelve a intentarlo."
  },
  "Explanations": {
   "slows_down_while_falling": "El objeto frena mientras todavía va cayendo. Ni la gravedad ni el aire pueden hacer eso.",
   "acceleration_grows": "El objeto acelera cada vez más mientras cae. La gravedad tira de forma constante, así que una caída real no hace eso.",
   "accelerates_upward": "El objeto acelera hacia el cielo, como si la gravedad tirara hacia arriba.",
   "impossible": "La forma en que se mueve este objeto rompe una ley de la física que cumple toda caída real.",
   "consistent": "El objeto acelera a un ritmo constante mientras cae, como hace caer las cosas la gravedad real.",
   "weak_violation": "Algo en el movimiento no cuadra, pero no con la claridad suficiente para llamarlo imposible.",
   "no_measurable_acceleration": "El objeto se mueve a velocidad constante, así que no hay una caída que medir.",
   "depth_change": "El objeto se acerca o se aleja de la cámara, y eso deforma demasiado su trayectoria en pantalla para medirla.",
   "too_few_samples": "El objeto aparece en muy pocos cuadros para medir su movimiento.",
   "no_measurable_events": "Pisa no encontró en este video una caída, un lanzamiento o un rebote que pudiera medir.",
   "pair_falls_apart": "Dos objetos soltados a la vez caen a ritmos distintos. Con gravedad real caen juntos, como mostró Galileo.",
   "bounce_gains_energy": "El objeto sale del rebote más rápido de lo que llegó. Un rebote real siempre pierde algo de energía.",
   "gravity_changes": "La gravedad cambia de fuerza de un vuelo al siguiente. En un video real, incluso en cámara lenta, se mantiene igual.",
   "camera_motion": "La cámara se mueve demasiado para medir el objeto contra el fondo.",
   "gravity_too_weak": "El objeto cae como si la gravedad fuera más débil que en la Tierra. Un video en cámara lenta se ve exactamente así, por eso Pisa no lo llama imposible.",
   "gravity_too_strong": "El objeto cae como si la gravedad fuera más fuerte que en la Tierra. Un video acelerado se ve así, por eso Pisa no lo llama imposible.",
   "no_free_flight": "En este video nada cae, vuela ni rebota por sí solo, así que no hay movimiento que Pisa pueda revisar.",
   "too_unclear": "Algo cae, vuela o rebota, pero es demasiado pequeño, borroso, oculto o breve para seguirlo."
  }
 },
 "zh-CN": {
  "WhatsApp": {
   "welcome": "你好，我是 Pisa。把有物体下落、被抛出或弹跳的视频转发给我，我会告诉你真实的物理能否产生这样的运动。我不检查人脸、声音或对口型。",
   "received": "收到。我正在测量视频中物体的运动，一分钟内回复你。Pisa 会在 24 小时内删除你的视频，只保留测量结果。",
   "onlyVideos": "我只能检查视频。把你想检查的视频转发给我。",
   "tooLarge": "这个视频超过 16 MB。请发送一个更短的视频，不超过 60 秒。",
   "rateLimited": "你在过去一小时内已经检查了很多视频。请稍后再试。",
   "busy": "Pisa 现在收到的视频太多。请过一会儿再试。",
   "frequentlyForwarded": "这个视频已被多次转发。",
   "details": "测量结果和证据：{link}",
   "tryAnother": "你可以换一个视频试试。",
   "legend": {
    "fit": "视频中，青柠色圆圈沿着真实重力允许的最接近的路径移动。",
    "earth_gravity": "视频中，青柠色圆圈显示地球重力会把它带到哪里。",
    "partner": "视频中，每个青柠色圆圈显示如果两者一起下落，物体会在哪里。",
    "elastic_bounce": "视频中，青柠色圆圈显示真实物理允许的最高弹跳。"
   }
  },
  "Verdict": {
   "physically_impossible": "物理上不可能",
   "consistent_with_real_physics": "符合真实物理",
   "inconclusive": "无法判定"
  },
  "Errors": {
   "unsupported_format": "Pisa 无法读取这个文件。请换成 MP4 或 MOV。",
   "video_too_long": "这个视频超过 60 秒。请剪到关键片段后再试。",
   "file_too_large": "这个文件超过 50 MB。",
   "unknown_duration": "Pisa 无法判断这个视频的时长。请重新导出为 MP4 再试。",
   "resolution_too_high": "这个视频的分辨率太高。请换成 4K 或更低的版本。",
   "transcode_failed": "Pisa 无法处理这个视频以进行测量。请重新导出为 MP4 再试。",
   "empty_window": "所选片段里没有可以测量的内容。",
   "paid_calls_disabled": "追踪功能暂时停用。请稍后再试。",
   "spend_cap_reached": "Pisa 暂时达到了分析次数上限。请稍后再试。",
   "network": "无法连接到 Pisa。请检查网络后再试。",
   "job_not_found": "找不到这次检查，可能已经过期。",
   "internal_error": "我们这边出了问题。请再试一次。"
  },
  "Explanations": {
   "slows_down_while_falling": "物体还在下落时却在减速。重力和空气都做不到这一点。",
   "acceleration_grows": "物体下落时越来越快地加速。重力的拉力是恒定的，真实的下落不会这样。",
   "accelerates_upward": "物体朝天空加速，好像重力在向上拉。",
   "impossible": "这个物体的运动方式违反了每一次真实下落都遵守的物理定律。",
   "consistent": "物体下落时以恒定的速率加速，和真实重力让物体下落的方式一致。",
   "weak_violation": "运动中有些地方不对劲，但还不够明确，不能判定为不可能。",
   "no_measurable_acceleration": "物体以恒定速度移动，没有可以测量的下落。",
   "depth_change": "物体在靠近或远离镜头，屏幕上的轨迹因此变形太大，无法测量。",
   "too_few_samples": "物体出现的帧数太少，无法测量它的运动。",
   "no_measurable_events": "Pisa 在这个视频里没有找到可以测量的下落、抛掷或弹跳。",
   "pair_falls_apart": "两个同时松手的物体以不同的速率下落。在真实重力下，它们会并排落下，正如伽利略所证明的。",
   "bounce_gains_energy": "物体弹起时比落下时还快。真实的弹跳总会损失一些能量。",
   "gravity_changes": "重力的强度在前后两段飞行之间发生了变化。在真实视频里，即使是慢动作，重力也保持不变。",
   "camera_motion": "镜头晃动太大，无法以背景为参照测量物体。",
   "gravity_too_weak": "物体下落得好像重力比地球上弱。慢动作视频看起来正是这样，所以 Pisa 不判定它不可能。",
   "gravity_too_strong": "物体下落得好像重力比地球上强。加速播放的视频看起来就是这样，所以 Pisa 不判定它不可能。",
   "no_free_flight": "这个视频里没有物体自行下落、飞行或弹跳，所以 Pisa 没有可以检查的运动。",
   "too_unclear": "有物体在下落、飞行或弹跳，但它太小、太模糊、被遮挡或太短暂，无法跟踪。"
  }
 },
 "pt-BR": {
  "WhatsApp": {
   "welcome": "Oi, eu sou o Pisa. Encaminhe um vídeo em que algo cai, é arremessado ou quica e eu digo se a física real poderia ter produzido isso. Não verifico rostos, vozes nem sincronia labial.",
   "received": "Recebido. Estou medindo como as coisas se movem e respondo em menos de um minuto. O Pisa apaga seu vídeo em até 24 horas e guarda só as medições.",
   "onlyVideos": "Só consigo verificar vídeos. Encaminhe o vídeo que você quer verificar.",
   "tooLarge": "Este vídeo tem mais de 16 MB. Envie um mais curto, de até 60 segundos.",
   "rateLimited": "Você já verificou muitos vídeos na última hora. Tente de novo mais tarde.",
   "busy": "O Pisa está recebendo muitos vídeos agora. Tente de novo daqui a pouco.",
   "frequentlyForwarded": "Este vídeo já foi encaminhado muitas vezes.",
   "details": "Medições e evidências: {link}",
   "tryAnother": "Você pode tentar com outro vídeo.",
   "legend": {
    "fit": "No vídeo, o círculo verde-limão segue o caminho mais próximo que a gravidade real permite.",
    "earth_gravity": "No vídeo, o círculo verde-limão mostra aonde a gravidade da Terra o levaria.",
    "partner": "No vídeo, cada círculo verde-limão mostra onde o objeto estaria se os dois caíssem juntos.",
    "elastic_bounce": "No vídeo, o círculo verde-limão mostra o quique mais alto que a física real permite."
   }
  },
  "Verdict": {
   "physically_impossible": "Fisicamente impossível",
   "consistent_with_real_physics": "Consistente com a física real",
   "inconclusive": "Inconclusivo"
  },
  "Errors": {
   "unsupported_format": "Este arquivo não é um vídeo que o Pisa consiga ler. Tente um MP4 ou MOV.",
   "video_too_long": "Este vídeo tem mais de 60 segundos. Corte-o no momento que importa e tente de novo.",
   "file_too_large": "Este arquivo tem mais de 50 MB.",
   "unknown_duration": "O Pisa não conseguiu saber a duração deste vídeo. Tente exportá-lo de novo como MP4.",
   "resolution_too_high": "A resolução deste vídeo é alta demais. Tente uma versão em 4K ou menos.",
   "transcode_failed": "O Pisa não conseguiu preparar este vídeo para a medição. Tente exportá-lo de novo como MP4.",
   "empty_window": "Não há nada para medir no trecho do vídeo selecionado.",
   "paid_calls_disabled": "O rastreamento está pausado no momento. Tente de novo mais tarde.",
   "spend_cap_reached": "O Pisa atingiu o limite de análises por enquanto. Tente de novo mais tarde.",
   "network": "Não foi possível conectar ao Pisa. Verifique sua conexão e tente de novo.",
   "job_not_found": "Não encontramos esta verificação. Ela pode ter expirado.",
   "internal_error": "Algo deu errado do nosso lado. Tente de novo."
  },
  "Explanations": {
   "slows_down_while_falling": "O objeto desacelera enquanto ainda está caindo. Nem a gravidade nem o ar fazem isso.",
   "acceleration_grows": "O objeto acelera cada vez mais enquanto cai. A gravidade puxa de forma constante, então uma queda real não faz isso.",
   "accelerates_upward": "O objeto acelera em direção ao céu, como se a gravidade puxasse para cima.",
   "impossible": "O jeito como este objeto se move quebra uma lei da física que toda queda real segue.",
   "consistent": "O objeto acelera a um ritmo constante enquanto cai, do jeito que a gravidade real faz as coisas caírem.",
   "weak_violation": "Algo no movimento parece errado, mas não com clareza suficiente para chamá-lo de impossível.",
   "no_measurable_acceleration": "O objeto se move a uma velocidade constante, então não há queda para medir.",
   "depth_change": "O objeto se aproxima ou se afasta da câmera, e isso distorce demais a trajetória na tela para medi-la.",
   "too_few_samples": "O objeto aparece em poucos quadros para medir o movimento.",
   "no_measurable_events": "O Pisa não encontrou neste vídeo uma queda, um arremesso ou um quique que pudesse medir.",
   "pair_falls_apart": "Dois objetos soltos ao mesmo tempo caem em ritmos diferentes. Com gravidade real eles caem lado a lado, como Galileu mostrou.",
   "bounce_gains_energy": "O objeto sai do quique mais rápido do que chegou. Um quique real sempre perde um pouco de energia.",
   "gravity_changes": "A gravidade muda de força de um voo para o outro. Num vídeo real, mesmo em câmera lenta, ela continua a mesma.",
   "camera_motion": "A câmera se move demais para medir o objeto em relação ao fundo.",
   "gravity_too_weak": "O objeto cai como se a gravidade fosse mais fraca que na Terra. Um vídeo em câmera lenta fica exatamente assim, por isso o Pisa não o chama de impossível.",
   "gravity_too_strong": "O objeto cai como se a gravidade fosse mais forte que na Terra. Um vídeo acelerado fica assim, por isso o Pisa não o chama de impossível.",
   "no_free_flight": "Neste vídeo nada cai, voa ou quica sozinho, então não há movimento que o Pisa possa verificar.",
   "too_unclear": "Algo cai, voa ou quica, mas é pequeno, borrado, escondido ou rápido demais para acompanhar."
  }
 }
}
"""
)
