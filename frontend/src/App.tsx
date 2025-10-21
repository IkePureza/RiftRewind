import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from '@/components/ui/select'
import { Loader2 } from 'lucide-react'

interface SummonerData {
  summoner: {
    name: string
    level: number
    puuid: string
  }
  topChampions: Array<{
    championId: number
    championLevel: number
    championPoints: number
    lastPlayTime: number
  }>
}

interface FetchSummonerParams {
  summonerName: string
  region: string
}

async function fetchSummonerData({ summonerName, region }: FetchSummonerParams): Promise<SummonerData> {
  const lambdaUrl = import.meta.env.VITE_LAMBDA_URL

  if (!lambdaUrl) {
    throw new Error('Lambda URL not configured. Please check .env.local file.')
  }

  const response = await fetch(lambdaUrl, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      summonerName,
      region,
    }),
  })

  const result = await response.json()

  // Check if Lambda returned a wrapped response with statusCode
  if (result.statusCode !== undefined) {
    if (result.statusCode === 200) {
      return JSON.parse(result.body)
    } else {
      const errorBody = JSON.parse(result.body)
      throw new Error(errorBody.error || 'Failed to fetch summoner data')
    }
  }

  // Function URL might return the data directly
  if (response.ok) {
    return result
  } else {
    throw new Error(result.error || 'Failed to fetch summoner data')
  }
}

function App() {
  const [gameName, setGameName] = useState('')
  const [region, setRegion] = useState('oc1')

  const mutation = useMutation({
    mutationFn: fetchSummonerData,
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    mutation.mutate({ summonerName: gameName, region })
  }

  return (
    <div className="min-h-screen">
      {/* Header */}
      <div className="bg-[#5383E8] py-16">
        <div className="container mx-auto px-4">
          <div className="text-center mb-8">
            <h1 className="text-5xl font-bold text-white mb-2">RIFT REWIND</h1>
            <p className="text-white/80 text-lg">League of Legends Player Search</p>
          </div>

          {/* Search Form */}
          <div className="max-w-3xl mx-auto">
            <form onSubmit={handleSubmit} className="flex gap-2">
              <div>
                <Select onValueChange={(val: string) => setRegion(val)} defaultValue={region}>
                  <SelectTrigger className="w-[160px] rounded-l-md">
                    <SelectValue placeholder="Region" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="na1">🇺🇸 NA</SelectItem>
                    <SelectItem value="euw1">🇪🇺 EUW</SelectItem>
                    <SelectItem value="eun1">🌍 EUNE</SelectItem>
                    <SelectItem value="kr">🇰🇷 KR</SelectItem>
                    <SelectItem value="br1">🇧🇷 BR</SelectItem>
                    <SelectItem value="la1">🌎 LAN</SelectItem>
                    <SelectItem value="la2">🌎 LAS</SelectItem>
                    <SelectItem value="oc1">🇦🇺 OCE</SelectItem>
                    <SelectItem value="tr1">🇹🇷 TR</SelectItem>
                    <SelectItem value="ru">🇷🇺 RU</SelectItem>
                    <SelectItem value="jp1">🇯🇵 JP</SelectItem>
                    <SelectItem value="ph2">🇵🇭 PH</SelectItem>
                    <SelectItem value="sg2">🇸🇬 SG</SelectItem>
                    <SelectItem value="th2">🇹🇭 TH</SelectItem>
                    <SelectItem value="tw2">🇹🇼 TW</SelectItem>
                    <SelectItem value="vn2">🇻🇳 VN</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <Input
                type="text"
                value={gameName}
                onChange={(e) => setGameName(e.target.value)}
                placeholder="Game Name + #TAG"
                required
                className="flex-1"
              />

              <Button type="submit" disabled={mutation.isPending} className="rounded-r-md">
                {mutation.isPending ? <Loader2 className="animate-spin h-4 w-4" /> : '.GG'}
              </Button>
            </form>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="bg-gray-50 min-h-[calc(100vh-280px)]">
        <div className="container mx-auto px-4 py-8">
          {/* Error Message */}
          {mutation.error && (
            <div className="max-w-3xl mx-auto mb-6">
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
                <strong className="font-semibold">Error: </strong>
                <span>{mutation.error.message}</span>
              </div>
            </div>
          )}

          {/* Results */}
          {mutation.data && (
            <div className="max-w-5xl mx-auto">
              {/* Summoner Info Card */}
              <Card className="mb-6">
                <CardContent className="p-6">
                  <div className="flex items-center gap-4">
                    <div className="w-20 h-20 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                      <span className="text-3xl font-bold text-white">
                        {mutation.data.summoner.name.charAt(0).toUpperCase()}
                      </span>
                    </div>
                    <div>
                      <h2 className="text-2xl font-bold text-gray-800">{mutation.data.summoner.name}</h2>
                      <p className="text-gray-600">Level {mutation.data.summoner.level}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Champion Mastery Section */}
              <Card>
                <CardHeader className="px-6">
                  <CardTitle className="text-xl">Champion Mastery</CardTitle>
                </CardHeader>
                <CardContent className="p-6">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {mutation.data.topChampions.map((champion, index) => (
                      <div
                        key={index}
                        className="bg-gradient-to-br from-gray-50 to-gray-100 rounded-lg p-4 border border-gray-200 hover:border-blue-400 transition-all hover:shadow-md"
                      >
                        <div className="flex justify-between items-start mb-3">
                          <div className="flex items-center gap-2">
                            <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center">
                              <span className="text-white font-bold text-sm">#{index + 1}</span>
                            </div>
                            <div>
                              <p className="text-sm text-gray-600">Champion ID</p>
                              <p className="font-semibold text-gray-800">{champion.championId}</p>
                            </div>
                          </div>
                        </div>
                        <div className="space-y-2">
                          <div className="flex justify-between items-center">
                            <span className="text-sm text-gray-600">Mastery Level</span>
                            <span className="font-semibold text-blue-600">{champion.championLevel}</span>
                          </div>
                          <div className="flex justify-between items-center">
                            <span className="text-sm text-gray-600">Points</span>
                            <span className="font-semibold text-gray-800">
                              {champion.championPoints.toLocaleString()}
                            </span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

          {/* Empty State */}
          {!mutation.data && !mutation.error && !mutation.isPending && (
            <div className="max-w-3xl mx-auto text-center py-12">
              <div className="text-gray-400 mb-4">
                <svg className="w-24 h-24 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-gray-600 mb-2">Search for a Summoner</h3>
              <p className="text-gray-500">Enter a summoner name and region to view their stats</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default App
