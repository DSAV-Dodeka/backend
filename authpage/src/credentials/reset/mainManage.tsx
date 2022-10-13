import '../../index.scss'
import React from 'react'
import {createRoot} from "react-dom/client";
import Manage from "./Manage";

const container = document.getElementById('root')
const root = createRoot(container!)
root.render(<React.StrictMode>
    <Manage />
</React.StrictMode>)