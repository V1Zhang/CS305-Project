import {defineStore} from 'pinia';
export const useMainStore = defineStore('myStore', {
    state: () => {
        return {
            username: "ZHANG V1",
            text: 0,
            name: "Foream Plank"
        }
    },
    actions: {
        login(message: { username: string }) {
            this.username = message.username
        },
        update(message: { text: number, name: string }) {
            this.text = message.text
            this.name = message.name
        },
    }
});

