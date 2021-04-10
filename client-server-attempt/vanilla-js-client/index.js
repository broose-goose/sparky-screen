
const MESSAGE_ACTIONS = {
    POWER_ON: 'POWER_ON',
    POWER_OFF: 'POWER_OFF',
    TOGGLE_GIF: 'TOGGLE_GIF',
    LOAD_GIFS: 'LOAD_GIFS',
    NO_GIFS: 'NO_GIFS'
}

const HandleMessage = (event) => {
    const serverMessage = JSON.parse(event.data)
    const { message = false, gifs = [] } = serverMessage
    if (
        message === false ||
        !Object.hasOwnProperty.call(MESSAGE_ACTIONS, message)
    ) {
        console.error('AHHHHH SHIT, THE SERVER RETURNED SOME GARBAGE D:')
    }
    const messageAction = MESSAGE_ACTIONS[message]
    switch(messageAction) {
        case MESSAGE_ACTIONS.POWER_ON:
            TurnPowerOn()
            break
        case MESSAGE_ACTIONS.POWER_OFF:
            TurnPowerOff()
            break
        case MESSAGE_ACTIONS.TOGGLE_GIF:
            SwitchGif()
            break
        case MESSAGE_ACTIONS.LOAD_GIFS:
            TryLoadGifs(gifs)
            break
        case MESSAGE_ACTIONS.NO_GIFS:
            ShowNoGifs()
            break
        default:
            console.error('AHHHHH SHIT, NOT EVEN SURE HOW I GOT HERE D:')
    }
}

const TurnPowerOn = () => {
    document.body.classList.remove('hide')
}

const TurnPowerOff = () => {
    document.body.classList.add('hide')
}

const SwitchGif = () => {
    const gifs = Array.from(document.querySelectorAll('img'))
    if (gifs.length === 0) {
        console.error('AHHHHH SHIT, THERE ARE NO GIFS IN THIS BITCH D:')
        return
    } else if (gifs.length === 1) {
        console.info('Can\'t switch gifs, there is only one :\'(')
        return
    }
    const currentGif = gifs.findIndex(gif => gif.classList.contains('show'))
    const nextGif = (currentGif + 1) % gifs.length
    gifs[currentGif].classList.remove('show')
    gifs[nextGif].classList.add('show')
}

const TryLoadGifs = (gifPaths = []) => {
    if (!Array.isArray(gifPaths)) {
        console.error('AHHHHH SHIT, THE SERVER DIDN\'T SEND OVER AN ARRAY OF GIF PATHS D:')
    } else if (gifPaths.length === 0) {
        console.error('AHHHHH SHIT, THE SERVER SENT THE WRONG MESSAGE TYPE... MAYBE? D:')
    }
    let gifHolder = new DocumentFragment();
    let gifWrapper = document.createElement('div')
    gifHolder.appendChild(gifWrapper)
    gifPaths.forEach((filePath, index) => {
        const img = document.createElement('img');
        img.src = filePath;
        if (index === 0) {
            img.classList.add('show');
        }
        gifWrapper.appendChild(img);
    })
    const replaceElement = document.querySelector('body > div')
    replaceElement.parentNode.replaceChild(gifHolder, replaceElement);
}

const ShowNoGifs = () => {
    window.confirm(
        'AGHHHH, NO GIFFS LOCATED ~/sparky-screen/gifs D: D:\n Load some GIFS and restart'
    )
}

const ShowGenericError = () => {
    window.confirm(
        'NOT SURE WHAT HAPPENED...\nCLOSING...\nPROBABLY RESTART THE COMPUTER...'
    )
}

window.addEventListener('DOMContentLoaded', () => {
    try {
        const socket = new WebSocket('ws://localhost:42069/ws')
        socket.onmessage = HandleMessage
        socket.onclose = ShowGenericError
    } catch (e) {
        console.error(e)
        ShowGenericError()
    }
})
