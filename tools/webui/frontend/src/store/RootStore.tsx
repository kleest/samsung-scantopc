import config, {Configuration} from "config";
import {UiStore} from "store/UiStore";
import React from "react";
import createApi from "services/api";
import {useTranslation} from "react-i18next";
import createConfig from "config";


export class RootStore {
    private config?: Configuration = undefined;
    public uiStore: UiStore;
    public api: any;

    constructor(config?: Configuration) {
        console.log("created new RootStore");
        this.uiStore = new UiStore(this);

        this.reconfig(config || createConfig());
    }

    reconfig(config: Configuration) {
        this.config = config;
        this.api = createApi(this.config);
    }
}

const RootStoreContext = React.createContext<RootStore | null>(null);

export function useRootStore() {
    const context = React.useContext(RootStoreContext);
    if (!context) {
        throw new Error("useRootStore must be used within RootStoreProvider");
    }
    return context;
}

type Props = {
    children?: React.ReactNode;
}

const rootStore = new RootStore();

export const RootStoreProvider : React.FunctionComponent<Props> = ({children}) => {
    return <RootStoreContext.Provider value={rootStore}>{children}</RootStoreContext.Provider>;
}
