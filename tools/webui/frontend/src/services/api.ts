import axios, { AxiosRequestConfig } from 'axios';
import {Configuration} from "config";
import {DocumentJson} from "ui/Document";

export default (config: Configuration) => {
    const apiClient = axios.create(config.api);

    const api = {
        getDocuments() {
            return apiClient.request({
                method: "get",
                url: `/documents/list`,
            });
        },
        getDocumentsOutDir() {
            return apiClient.request({
                method: "get",
                url: `/documents/list_outdir`,
            });
        },
        setDocument(id: string, data: DocumentJson) {
            return apiClient.request({
                method: "post",
                url: `/documents/${id}`,
                data: data,
            });
        },
        moveDocumentToOutDir(id: string) {
            return apiClient.request({
                method: "post",
                url: `/documents/${id}/move_to_outdir`,
            });
        },
        deleteDocument(id: string) {
            return apiClient.request({
                method: "delete",
                url: `/documents/${id}`,
            });
        },
        mergeDocuments(ids: string[], name: string) {
            return apiClient.request({
                method: "post",
                url: `/documents/merge`,
                data: {ids, name}
            });
        },
        getDocumentUrl(id: string, download: boolean) {
            return apiClient.getUri({
                url: `/documents/${id}${download && "/download" || ""}`
            });
        },
    };

    return {
        ...api
    };
};
