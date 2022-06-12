import * as React from 'react';
import * as ReactDOM from "react-dom";

import App from './App';
import "./styles.scss";


if (!new class { x: any }().hasOwnProperty('x')) throw new Error('Transpiler is not configured correctly');

let mountNode = document.getElementById("root");
ReactDOM.render(<App />, mountNode);

/* react 18
const root = createRoot(mountNode!);
root.render(<App name="Jane" />);
*/
