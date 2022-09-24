import './index.scss'
import React from 'react'
import {createRoot} from "react-dom/client";
import ContainBack from "./ContainBack";
import Register from "./Register";


const container = document.getElementById('root')
const root = createRoot(container!)
root.render(<React.StrictMode>
    <ContainBack component={<Register />} />
</React.StrictMode>)