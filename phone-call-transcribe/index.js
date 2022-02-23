const WebSocket = require("ws");
const express = require("express");
const WaveFile = require("wavefile").WaveFile;

const path = require("path")
const app = express();
const server = require("http").createServer(app);
const wss = new WebSocket.Server({ server });

let assembly;
let chunks = [];

// Handle Web Socket Connection
wss.on("connection", function connection(ws) {
  console.log("New Connection Initiated");

  ws.on("message", function incoming(message) {
    if (!assembly)
      return console.error("AssemblyAI's WebSocket must be initialized.");

    const msg = JSON.parse(message);
    switch (msg.event) {
      case "connected":
        console.log(`A new call has connected.`);
        assembly.onerror = console.error;
        const texts = {};
        assembly.onmessage = (assemblyMsg) => {
      	  const res = JSON.parse(assemblyMsg.data);
      	  texts[res.audio_start] = res.text;
      	  const keys = Object.keys(texts);
      	  keys.sort((a, b) => a - b);
          let msg = '';
      	  for (const key of keys) {
            if (texts[key]) {
              msg += ` ${texts[key]}`;
            }
          }
          console.log(msg);
          wss.clients.forEach( client => {
            if (client.readyState === WebSocket.OPEN) {
              client.send(
                JSON.stringify({
                  event: "interim-transcription",
                  text: msg
                })
              );
            }
          });
        };
        break;
      case "start":
        console.log(`Starting Media Stream ${msg.streamSid}`);
        break;
      case "media":
        const twilioData = msg.media.payload;
        // Build the wav file from scratch since it comes in as raw data
        let wav = new WaveFile();

        // Twilio uses MuLaw so we have to encode for that
        wav.fromScratch(1, 8000, "8m", Buffer.from(twilioData, "base64"));
        
        // This library has a handy method to decode MuLaw straight to 16-bit PCM
        wav.fromMuLaw();
        
        // Get the raw audio data in base64
        const twilio64Encoded = wav.toDataURI().split("base64,")[1];
        
        // Create our audio buffer
        const twilioAudioBuffer = Buffer.from(twilio64Encoded, "base64");
                    
        // Send data starting at byte 44 to remove wav headers so our model sees only audio data
        chunks.push(twilioAudioBuffer.slice(44));
                    
        // We have to chunk data b/c twilio sends audio durations of ~20ms and AAI needs a min of 100ms
        if (chunks.length >= 5) {
          const audioBuffer = Buffer.concat(chunks);
          const encodedAudio = audioBuffer.toString("base64");
          assembly.send(JSON.stringify({ audio_data: encodedAudio }));
          chunks = [];
        }
        break;
      case "stop":
        console.log(`Call Has Ended`);
        assembly.send(JSON.stringify({ terminate_session: true }));
        break;
    }
  });
});

//Handle HTTP Request
app.get("/", (req, res) => res.sendFile(path.join(__dirname, "/index.html")));

app.post("/", async (req, res) => {
  assembly = new WebSocket(
    "wss://api.assemblyai.com/v2/realtime/ws?sample_rate=8000",
    { headers: { authorization: "YOUR_ASSEMBLYAI_API_KEY" } }
  );

  res.set("Content-Type", "text/xml");
  res.send(
    `<Response>
       <Start>
         <Stream url='wss://${req.headers.host}' />
       </Start>
       <Say>
         Start speaking to see your audio transcribed in the console
       </Say>
       <Pause length='30' />
     </Response>`
  );
});

// Start server
console.log("Listening at Port 8080");
server.listen(8080);