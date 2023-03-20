import {RootStore, useRootStore} from "store/RootStore";
import {action, makeAutoObservable, runInAction} from "mobx";
import {fromPromise} from "mobx-utils";
import {DocumentJson} from "ui/Document";
import {ApiTypes} from "services/apiTypes";

export class UiStore {
    private root: RootStore;

    documents: ApiTypes.DocumentList = [];
    documentsOut: ApiTypes.DocumentList = [];
    documentsListPromise: any;
    documentsListOutPromise: any;
    documentsSetPromise: any;
    documentsMoveToOutPromise: any;
    documentsDeletePromise: any;
    documentsMergePromise: any;

    // PDF preview
    previewUrl: string = "";

    // merge dialog
    mergeDocuments: string[] = [];

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
                // clear merge list since some documents may have been moved
                this.mergeDocuments = [];
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
        this.documentsMoveToOutPromise = fromPromise(prms);

        try {
            await prms;
        } catch (err) {
            console.log(err);
        } finally {
            await this.getDocuments();
            await this.getDocumentsOut();
        }
    }
    async deleteDocument(i: number) {
        const prms = this.root.api.deleteDocument(this.documents[i].id);
        this.documentsDeletePromise = fromPromise(prms);

        try {
            await prms;
        } catch (err) {
            console.log(err);
        } finally {
            await this.getDocuments();
        }
    }
    async doMergeDocuments(ids: string[], name: string) {
        const prms = this.root.api.mergeDocuments(ids, name);
        this.documentsMergePromise = fromPromise(prms);

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

    findDocument(id: string) {
        return this.documents.find((document) => document.id === id);
    }

    addMergeDocument(id: string) {
        this.mergeDocuments.push(id);
    }

    removeMergeDocument(id: string) {
        const ix = this.mergeDocuments.indexOf(id);
        if (ix >= 0)
            this.mergeDocuments.splice(ix, 1);
    }

    moveMergeDocument(id: string, offset: number) {
        const ix = this.mergeDocuments.indexOf(id);
        if (ix >= 0) {
            const el = this.mergeDocuments.splice(ix, 1)[0];
            this.mergeDocuments.splice(ix + offset, 0, el);
        }
    }

    // computed
    get mergeDocumentsFull(): ApiTypes.DocumentList {
        return this.mergeDocuments.map((id) => this.findDocument(id)!);
    }

    constructor(root: RootStore) {
        this.root = root;

        makeAutoObservable(this);
    }
}

export function useUiStore() {
    return useRootStore().uiStore;
}
