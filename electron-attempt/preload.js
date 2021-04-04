
const fsp = require('fs/promises');
const os = require('os');
const path = require('path');
const chokidar = require('chokidar');

const shell = require('shelljs');

const GIF_FOLDER = path.join(os.homedir(), '.config', 'gif-viewer');
const GIF_REGEX = /.+?.gif$/i;

const ReadGifs = async () => {
  try {
    shell.mkdir('-p', GIF_FOLDER);
    const files = await fsp.readdir(GIF_FOLDER);
    const gifFiles = files.filter(file => GIF_REGEX.test(file))
    if (gifFiles.length === 0) {
      alert('No gifs located ~/.config/gif-viewer D:')
      return
    }
    let gifHolder = new DocumentFragment();
    let gifWrapper = document.createElement('div')
    gifHolder.appendChild(gifWrapper)
    gifFiles.forEach((file, index) => {
      const filePath = path.join('file://', GIF_FOLDER, file);
      const img = document.createElement('img');
      img.src = filePath;
      if (index === 0) {
        img.classList.add('show');
      }
      gifWrapper.appendChild(img);
    })
    const replaceElement = document.querySelector('body > div')
    replaceElement.parentNode.replaceChild(gifHolder, replaceElement);
  } catch (e) {
    console.log(e)
    alert("WELL WE DONE DID MESSED UP HERE, YA HEARD?")
  }
}

let toggleFlag = false

const SwitchGif = () => {
  if (toggleFlag) {
    return
  }
  toggleFlag = true
  const gifs = Array.from(document.querySelectorAll('img'))
  const currentGif = gifs.findIndex(gif => gif.classList.contains('show'))
  const nextGif = (currentGif + 1) % gifs.length
  gifs[currentGif].classList.remove('show')
  gifs[nextGif].classList.add('show')
}

const ResetToggleFlag = () => {
  if (!toggleFlag) {
    return
  }
  toggleFlag = false
}

const TurnPowerOn = () => {
  document.body.classList.remove('hide')
}

const TurnPowerOff = () => {
  document.body.classList.add('hide')
}

const HandleKeydown = (event) => {
  switch (event.keyCode) {
    case 32:
      // space bar
      TurnPowerOff();
      break;
    case 39:
      // right arrow
      SwitchGif();
      break;
  }
}

const HandleKeyup = (event) => {
  switch (event.keyCode) {
    case 32:
      // space bar
      TurnPowerOn();
      break;
    case 39:
      // right arrow
      ResetToggleFlag();
      break;
  }
}

const HandleToggleButton = (err, value) => {
  if (value) {
    SwitchGif();
  } else {
    ResetToggleFlag();
  }
}

const HandlePowerButton = (err, value) => {
  if (value) {
    TurnPowerOff();
  } else {
    TurnPowerOn();
  }
}

let toggleButton = null;
let powerButton = null;

window.addEventListener('DOMContentLoaded', () => {
  chokidar.watch(GIF_FOLDER, { persistent: true, ignoreInitial: true})
      .on('add', ReadGifs)
      .on('unlink', ReadGifs);
  ReadGifs().then()
  if (process.arch !== 'arm') {
    window.addEventListener('keydown', HandleKeydown)
    window.addEventListener('keyup', HandleKeyup)
    window.addEventListener('beforeunload', () => {
      window.removeEventListener('keydown', HandleKeydown)
      window.removeEventListener('keyup', HandleKeyup)
    })
  } else {
    const Gpio = require('onoff').Gpio;
    toggleButton = new Gpio(21, 'in', 'both', { debounceTimeout: 10 })
    toggleButton.watch(HandleToggleButton);
    powerButton = new Gpio(20, 'in', 'both', { debounceTimeout: 10 })
    toggleButton.watch(HandlePowerButton);
    process.addListener('SIGINT', _ => {
      toggleButton.unexport();
      powerButton.unexport();
    });
  }
})
