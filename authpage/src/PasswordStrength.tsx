import React from "react";
import { zxcvbn, zxcvbnOptions } from '@zxcvbn-ts/core'
import zxcvbnCommonPackage from '@zxcvbn-ts/language-common'

export interface Props {
    password: string;
}

const mapper = (score: number): string => {
    return ['weak', 'weak', 'okay', 'good', 'strong'].at(score) || 'weak'
}

const PasswordStrength: React.FC<Props> = (props) => {

    zxcvbnOptions.setOptions({
        dictionary: zxcvbnCommonPackage.dictionary,
        graphs: zxcvbnCommonPackage.adjacencyGraphs,
    })

    const score = zxcvbn(props.password).score

    return (
        <div className={"passBar" + (score + 1)}>Your password is <strong>{mapper(score)}</strong></div>
    )
}

export { PasswordStrength as default }
