import {RootStore, useRootStore} from "store/RootStore";
import {action, makeObservable, observable, runInAction} from "mobx";
import {fromPromise} from "mobx-utils";
import {DocumentJson} from "ui/Document";

export class UiStore {
    private root: RootStore;

    documents: any = [];
    documentsOut: any = [];
    documentsListPromise: any;
    documentsListOutPromise: any;
    documentsSetPromise: any;
    documentsMoveToOutPromise: any;

    // PDF preview
    previewUrl: any = "";

    // actions
    getDocuments = async () => {
        const prms = this.root.api.getDocuments();
        this.documentsListPromise = fromPromise(prms);

        let result: [] = [];
        try {
            const res = await prms;
            result = res.data;
        } catch (err) {
            console.log(err);
        } finally {
            runInAction(() => {
                this.documents = result;
            });
        }
    };
    getDocumentsOut = async () => {
        const prms = this.root.api.getDocumentsOutDir();
        this.documentsListOutPromise = fromPromise(prms);

        let result: [] = [];
        try {
            const res = await prms;
            result = res.data;
        } catch (err) {
            console.log(err);
        } finally {
            runInAction(() => {
                this.documentsOut = result;
            });
        }
    };
    setDocument = async(i: number, data: DocumentJson) => {
        // close preview if we are going to modify the currently previewed document
        if (this.documentUrl(i, false) === this.previewUrl)
            this.setPDFPreview("");

        const prms = this.root.api.setDocument(this.documents[i].id, data);
        this.documentsSetPromise = fromPromise(prms);

        try {
            const res = await prms;
        } catch (err) {
            console.log(err);
        } finally {
            await this.getDocuments();
        }
    }
    moveDocumentToOutDir = async(i: number) => {
        const prms = this.root.api.moveDocumentToOutDir(this.documents[i].id);
        this.documentsSetPromise = fromPromise(prms);

        try {
            await prms;
        } catch (err) {
            console.log(err);
        } finally {
            await this.getDocuments();
            await this.getDocumentsOut();
        }
    }

    documentUrl = (i: number, download: boolean) => {
        return this.root.api.getDocumentUrl(this.documents[i].id, download);
    }

    setPDFPreview = (url: string) => {
        this.previewUrl = url;
    }

    constructor(root: RootStore) {
        this.root = root;

        makeObservable(this, {
            documents: observable,
            documentsOut: observable,
            documentsListPromise: observable,
            documentsListOutPromise: observable,
            documentsMoveToOutPromise: observable,
            documentsSetPromise: observable,
            previewUrl: observable,
            getDocuments: action,
        });
    }
}

export function useUiStore() {
    return useRootStore().uiStore;
}
