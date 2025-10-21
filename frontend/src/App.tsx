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

interface MatchData {
  matchId: string
  champion: string
  championId: number
  role: string
  kills: number
  deaths: number
  assists: number
  kda: string
  win: boolean
  gameMode: string
  gameDuration: number
  cs: number
  s3Key: string
}

interface SummonerData {
  summoner: {
    name: string
    level: number
    puuid: string
    profileS3Key: string
  }
  matchesProcessed: number
  matches: MatchData[]
  region: string
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

              {/* Match History Section */}
              <Card>
                <CardHeader className="px-6">
                  <CardTitle className="text-xl">
                    Recent Match History ({mutation.data.matchesProcessed} matches)
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-6">
                  <div className="space-y-3">
                    {mutation.data.matches.map((match) => (
                      <div
                        key={match.matchId}
                        className={`rounded-lg p-4 border-2 transition-all hover:shadow-md ${
                          match.win
                            ? 'bg-blue-50 border-blue-200 hover:border-blue-400'
                            : 'bg-red-50 border-red-200 hover:border-red-400'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-4">
                            {/* Champion Icon Placeholder */}
                            <div className="w-16 h-16 bg-gradient-to-br from-purple-500 to-blue-600 rounded-lg flex items-center justify-center">
                              <span className="text-white font-bold text-lg">
                                {match.champion.substring(0, 2).toUpperCase()}
                              </span>
                            </div>

                            {/* Match Info */}
                            <div>
                              <div className="flex items-center gap-2 mb-1">
                                <h3 className="font-bold text-lg text-gray-800">{match.champion}</h3>
                                <span className={`px-2 py-0.5 rounded text-xs font-semibold ${
                                  match.win
                                    ? 'bg-blue-600 text-white'
                                    : 'bg-red-600 text-white'
                                }`}>
                                  {match.win ? 'Victory' : 'Defeat'}
                                </span>
                              </div>
                              <div className="flex items-center gap-3 text-sm text-gray-600">
                                <span className="font-semibold">{match.role || 'UNKNOWN'}</span>
                                <span>•</span>
                                <span>{match.gameMode}</span>
                                <span>•</span>
                                <span>{Math.floor(match.gameDuration / 60)}m {match.gameDuration % 60}s</span>
                              </div>
                            </div>
                          </div>

                          {/* Stats */}
                          <div className="flex items-center gap-6">
                            <div className="text-center">
                              <div className="text-2xl font-bold text-gray-800">
                                {match.kills}/{match.deaths}/{match.assists}
                              </div>
                              <div className="text-xs text-gray-500">KDA</div>
                            </div>
                            <div className="text-center">
                              <div className="text-xl font-semibold text-gray-800">{match.cs}</div>
                              <div className="text-xs text-gray-500">CS</div>
                            </div>
                            <div className="text-center">
                              <div className="text-lg font-medium text-gray-600">
                                {match.deaths === 0
                                  ? 'Perfect'
                                  : ((match.kills + match.assists) / match.deaths).toFixed(2)}
                              </div>
                              <div className="text-xs text-gray-500">Ratio</div>
                            </div>
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
