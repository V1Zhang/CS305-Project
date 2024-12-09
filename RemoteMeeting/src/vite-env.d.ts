/// <reference types="vite/client" />
declare module '*vue' {
    import {ComponentOptions} from "vue";
    const ComponentOptions: ComponentOptions
    export default ComponentOptions
}
declare module 'vue-core-video-player' {
    import {App, Plugin} from 'vue'

    const VueCoreVideoPlayerPlugin: Plugin
    export default VueCoreVideoPlayerPlugin

    export function install(app: App, ...options: any[]): void
}
declare module 'flask_cors' {
    import {Application} from 'flask';

    export function CORS(
        app: Application,
        resources?: string | RegExp | Record<string, any>,
        options?: CORSOptions
    ): void;
}
