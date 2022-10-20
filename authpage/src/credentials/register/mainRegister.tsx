import '../../index.scss'
import React from 'react'
import {createRoot} from "react-dom/client";
import Register from "./Register";


const container = document.getElementById('root')
const root = createRoot(container!)
root.render(<React.StrictMode>
    <Register />
</React.StrictMode>)